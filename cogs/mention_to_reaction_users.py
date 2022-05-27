import contextlib
import io
import json
import logging
import os
from typing import Optional, Dict, List, Union

import discord.ext.commands
import gspread
import dispander.module

import utils.misc
from cogs.cog import CogBase, ArgumentError
from utils.discord import find_text_channel, find_reaction_users, find_no_reaction_users
from utils.gspread_client import GSpreadClient


logger = logging.getLogger(__name__)


class _NormalCommand:
    def __init__(self, bot):
        self.bot = bot
        self._message_id: Optional[int] = None
        self._reaction_emoji: Optional[str] = None
        self._use_ignore_list = True
        self._expand_message = False

    def parse_args(self, args: Dict[str, str]):
        if "message" not in args:
            raise ArgumentError(message="対象のメッセージIDを必ず指定してください")
        if "reaction" not in args:
            raise ArgumentError(reaction="対象のリアクションを必ず指定してください")

        self._message_id = int(args["message"])
        self._reaction_emoji = args["reaction"]
        # 通常モードではignore_listはデフォルトで利用する
        self._use_ignore_list = utils.misc.get_boolean(args, "ignore_list", True)
        self._expand_message = utils.misc.get_boolean(args, "expand_message", False)

    async def execute(
        self, ctx: discord.ext.commands.context.Context, ignore_ids: List[int]
    ):
        # 無視リストを使わない
        if not self._use_ignore_list:
            ignore_ids.clear()

        channel, message = await find_text_channel(ctx.guild, self._message_id)

        if channel is None:
            logger.error(f"not found channel, message_id={self._message_id}")
            await ctx.send(
                f"チャンネルが見つかりませんでした。メッセージID: `{self._message_id}` が正しいか確認してください。"
            )
            return

        logger.debug(
            f"fetch message: channel={channel.name}, message={message.content}"
        )

        if self._reaction_emoji.lower() == "none":
            # リアクションをしていないユーザーを探す
            logger.debug("find no reaction users")
            title = "リアクションしていない"
            targets = self._filter_users(channel.members, message, ignore_ids)
            result = await find_no_reaction_users(message, targets)
        elif self._reaction_emoji.lower() == "all":
            # リアクションしている全てのユーザーを探す
            logger.debug("find all reaction users")
            title = "リアクションしている"
            result = []
            for reaction in message.reactions:
                users = [user async for user in reaction.users()]
                result.extend(self._filter_users(users, message, ignore_ids))
        else:
            # 指定の絵文字でリアクションしているユーザーを探す
            logger.debug(f"find reaction users: emoji={self._reaction_emoji}")
            title = f"{self._reaction_emoji} をリアクションしている"
            targets = await find_reaction_users(message, self._reaction_emoji)
            result = self._filter_users(targets, message, ignore_ids)

        logger.debug("send result")
        if len(result) > 0:
            title = f"{title}ユーザーは以下の通りです"
            # 重複は除く
            description = ", ".join([user.mention for user in list(set(result))])
        else:
            title = f"{title}ユーザーは居ませんでした"
            description = ""
        embed = discord.Embed(title=title, description=description)
        embed.add_field(name="対象のメッセージ", value=message.jump_url, inline=False)

        await ctx.send(embed=embed)

        if self._expand_message:
            await self._send_expand_message(ctx, message)

    @staticmethod
    def _filter_users(
        users: List[Union[discord.Member, discord.User]],
        m: discord.Message,
        ignore_ids: List[int],
    ) -> List[Union[discord.Member, discord.User]]:
        # BOTではない かつ メッセージの投稿者ではない かつ 無視リストに含まれていない
        return [
            user
            for user in users
            if not user.bot and user.id != m.author.id and user.id not in ignore_ids
        ]

    # copy and modify from dispander method
    @staticmethod
    async def _send_expand_message(ctx, message):
        if message.content or message.attachments:
            await ctx.send(embed=dispander.module.compose_embed(message))
        # Send the second and subsequent attachments with embed (named 'embed') respectively:
        for attachment in message.attachments[1:]:
            embed = discord.Embed()
            embed.set_image(url=attachment.proxy_url)
            await ctx.send(embed=embed)
        for embed in message.embeds:
            await ctx.send(embed=embed)


class _ManageCommand:
    def __init__(self):
        self._use_ignore_list = False
        self._download = False
        self._append: Optional[str] = None
        self._remove: Optional[str] = None
        self._show = False

    def parse_args(self, args: Dict[str, str]):
        self._use_ignore_list = utils.misc.get_boolean(args, "ignore_list")
        self._download = utils.misc.get_boolean(args, "download")
        self._append = args.get("append", None)
        self._remove = args.get("remove", None)
        self._show = utils.misc.get_boolean(args, "show")

    async def execute(
        self,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
    ):
        if self._use_ignore_list:
            await self._manage_ignore_list(ctx, worksheet, ignore_ids)

    async def _manage_ignore_list(
        self,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
    ):
        if self._append is not None:
            await self._append_ignore_list(
                ctx, worksheet, ignore_ids, int(self._append)
            )
        if self._remove is not None:
            await self._remove_ignore_list(ctx, worksheet, ignore_ids, self._remove)
        if self._download:
            await self._download_ignore_list(ctx, worksheet, ignore_ids)
        if self._show:
            await self._show_ignore_list(ctx, worksheet, ignore_ids)

    @classmethod
    async def _download_ignore_list(
        cls,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
    ):
        filename = f"ignore_list_{ctx.guild.id}.json"
        logger.debug(
            f"download ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, json={filename}"
        )
        ignore_dict = []
        for user_id in ignore_ids:
            user = ctx.guild.get_member(user_id)
            if user is None:
                # 既にサーバーから抜けている場合も考慮する
                ignore_dict.append(
                    dict(id=user_id, name="Not Found", display_name="Not Found")
                )
            else:
                ignore_dict.append(
                    dict(id=user.id, name=user.name, display_name=user.display_name)
                )
        with contextlib.closing(io.StringIO()) as buffer:
            json.dump(
                ignore_dict,
                buffer,
                default=utils.misc.parse_json,
                indent=2,
                ensure_ascii=False,
            )
            buffer.seek(0)
            await ctx.send(file=discord.File(buffer, filename))

    @classmethod
    async def _append_ignore_list(
        cls,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
        append_id: int,
    ):
        logger.debug(
            f"append ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, user={append_id}"
        )
        member = ctx.guild.get_member(append_id)
        if member is None:
            logger.debug(
                f"append ignore_list: not found user_id={append_id} from guild_id={ctx.guild.id}"
            )
            await ctx.send(f"ユーザーが見つかりませんでした。 user_id={append_id}")
            return

        ignore_ids.append(append_id)
        cls._update_cells(worksheet, [str(ignore_id) for ignore_id in ignore_ids])
        await ctx.send(
            f"{member.display_name}[{append_id}] を {ctx.guild.name}[{ctx.guild.id}] の無視リストに追加しました。"
        )

    @classmethod
    async def _remove_ignore_list(
        cls,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
        remove: str,
    ):
        # intのリストに空の要素が追加できないのでstrにしている
        ignore_list = [str(ignore_id) for ignore_id in ignore_ids]

        if remove.lower() == "all":
            logger.debug(
                f"remove ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, user=all"
            )
            # 要素数は変えずに空文字で埋めて全削除
            ignore_list = ["" for _ in ignore_list]
            output_text = f"{ctx.guild.name}[{ctx.guild.id}] の無視リストから全てのユーザーを除去しました。"
            cls._update_cells(worksheet, ignore_list)
        else:
            remove_id = int(remove)
            logger.debug(
                f"remove ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, user={remove_id}"
            )
            if remove_id in ignore_ids:
                # 要素数は変えずに空文字で埋めて削除
                ignore_list.remove(str(remove_id))
                ignore_list.append("")
                output_text = f"{ctx.guild.name}[{ctx.guild.id}] の無視リストから user_id={remove_id} を除去しました。"
                cls._update_cells(worksheet, ignore_list)
            else:
                logger.debug(
                    f"remove ignore_list: not contains user_id={remove_id} in guild_id={ctx.guild.id}"
                )
                output_text = f"{ctx.guild.name}[{ctx.guild.id}] の無視リストに user_id={remove_id} が存在しません。"

        await ctx.send(output_text)

    @classmethod
    async def _show_ignore_list(
        cls,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: List[int],
    ):
        logger.debug(f"show ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}")
        embed = discord.Embed(
            title="/mention_to_reaction_users 無視リスト",
            description=f"サーバー: {ctx.guild.name}[{ctx.guild.id}]",
        )
        if len(ignore_ids) == 0:
            embed.add_field(name="なし", value="", inline=False)
        for user_id in ignore_ids:
            user = ctx.guild.get_member(user_id)
            if user is None:
                embed.add_field(name="[Not Found]", value=f"{user_id}", inline=False)
            else:
                embed.add_field(
                    name=f"{user.display_name}", value=f"{user_id}", inline=False
                )
        await ctx.send(embed=embed)

    @staticmethod
    def _update_cells(worksheet: gspread.worksheet.Worksheet, values: List[str]):
        cells = worksheet.range(f"A1:A{len(values)}")
        for index, cell in enumerate(cells):
            cell.value = values[index]
        worksheet.update_cells(cells)


class MentionToReactionUsers(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self, bot)
        self._gspread_client = GSpreadClient()
        self._normal_command: Optional[_NormalCommand] = None
        self._manage_command: Optional[_ManageCommand] = None

    @discord.ext.commands.command()
    async def mention_to_reaction_users(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: Dict[str, str]):
        use_manage = utils.misc.get_boolean(args, "manage")
        if use_manage:
            self._manage_command = _ManageCommand()
            self._manage_command.parse_args(args)
        else:
            self._normal_command = _NormalCommand(self.bot)
            self._normal_command.parse_args(args)

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        # NOTE: シートの取得も1度だけでいいかもしれない
        sheet_id = os.environ["IGNORE_LIST_SHEET_ID"]
        workbook = self._gspread_client.open_by_key(sheet_id)
        sheet_name = str(ctx.guild.id)
        worksheet = utils.gspread_client.get_or_add_worksheet(
            workbook,
            sheet_name,
            lambda w, n: w.add_worksheet(n, rows=100, cols=1),
        )
        ignore_list = worksheet.col_values(1)
        ignore_ids = [int(ignore_id) for ignore_id in ignore_list]
        logger.debug(f"fetch ignore_ids: ignore_ids={ignore_ids}")

        # Cog自体は使い回すのでCommandは毎回破棄する
        if self._manage_command is not None:
            await self._manage_command.execute(ctx, worksheet, ignore_ids)
            self._manage_command = None

        if self._normal_command is not None:
            await self._normal_command.execute(ctx, ignore_ids)
            self._normal_command = None


def setup(bot):
    return bot.add_cog(MentionToReactionUsers(bot))
