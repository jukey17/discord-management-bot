import contextlib
import copy
import io
import json
import logging
import os
from typing import Optional, Dict, List, Union

import discord.ext.commands
import dispander.module
from discord.ext.commands import Bot, Context, Cog, command
from discord_ext_commands_coghelper import (
    ArgumentError,
    CogHelper,
    ExecutionError,
    ChannelNotFoundError,
    UserNotFoundError,
)
from discord_ext_commands_coghelper.utils import get_bool, find_text_channel

from gspread import Worksheet

from utils.gspread_client import GSpreadClient, get_or_add_worksheet
from utils.misc import parse_json

logger = logging.getLogger(__name__)


async def _find_no_reaction_users(
    message: discord.Message, candidates: List[Union[discord.Member, discord.User]]
) -> List[Union[discord.Member, discord.User]]:
    result = copy.copy(candidates)
    for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        for candidate in candidates:
            if candidate not in result:
                continue
            for user in users:
                if candidate.id == user.id:
                    result.remove(candidate)

    return result


async def _find_reaction_users(
    message: discord.Message, emoji: str
) -> List[Union[discord.Member, discord.User]]:
    target = None
    for reaction in message.reactions:
        if isinstance(reaction.emoji, discord.Emoji):
            # カスタム絵文字は名前が含まれているか見る ※:{name}:の形式なはずなので
            if reaction.emoji.name not in emoji:
                continue
        if isinstance(reaction.emoji, discord.PartialEmoji):
            # Partial絵文字も名前が含まれているか見る
            if reaction.emoji.id is None:
                continue
            if reaction.emoji.name not in emoji:
                continue
        if isinstance(reaction.emoji, str):
            # Unicode絵文字は完全一致でOK
            if reaction.emoji != emoji:
                continue
        target = reaction
        break

    if target is None:
        return []
    return [user async for user in target.users()]


class _NormalCommand:
    def __init__(self):
        self._message_id: Optional[int] = None
        self._reaction_emoji: Optional[str] = None
        self._use_ignore_list = True
        self._expand_message = False

    def parse_args(self, ctx: Context, args: Dict[str, str]):
        if "message" not in args:
            raise ArgumentError(ctx, message="対象のメッセージIDを必ず指定してください")
        if "reaction" not in args:
            raise ArgumentError(ctx, reaction="対象のリアクションを必ず指定してください")

        try:
            self._message_id = int(args["message"])
        except ValueError:
            raise ArgumentError(ctx, message="メッセージIDの指定が正しくありません")

        self._reaction_emoji = args["reaction"]
        # 通常モードではignore_listはデフォルトで利用する
        self._use_ignore_list = get_bool(args, "ignore_list", True)
        self._expand_message = get_bool(args, "expand_message", False)

    async def execute(self, ctx: Context, ignore_ids: List[int]):
        # 無視リストを使わない
        if not self._use_ignore_list:
            ignore_ids.clear()

        channel, message = await find_text_channel(ctx.guild, self._message_id)

        if channel is None:
            raise ChannelNotFoundError(
                ctx, channel_id="None", message_id=self._message_id
            )

        logger.debug(
            f"fetch message: channel={channel.name}, message={message.content}"
        )

        if self._reaction_emoji.lower() == "none":
            # リアクションをしていないユーザーを探す
            logger.debug("find no reaction users")
            title = "リアクションしていない"
            targets = self._filter_users(channel.members, message, ignore_ids)
            result = await _find_no_reaction_users(message, targets)
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
            targets = await _find_reaction_users(message, self._reaction_emoji)
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
        self._append: Optional[int] = None
        self._remove: Optional[str] = None
        self._show = False

    def parse_args(self, ctx: Context, args: Dict[str, str]):
        self._use_ignore_list = get_bool(args, "ignore_list")
        self._download = get_bool(args, "download")
        try:
            self._append = int(args.get("append", -1))
        except ValueError:
            raise ArgumentError(ctx, append="ユーザーIDの指定が正しくありません")

        self._remove = args.get("remove", None)
        self._show = get_bool(args, "show")

    async def execute(self, ctx: Context, worksheet: Worksheet, ignore_ids: List[int]):
        if self._use_ignore_list:
            await self._manage_ignore_list(ctx, worksheet, ignore_ids)

    async def _manage_ignore_list(
        self, ctx: Context, worksheet: Worksheet, ignore_ids: List[int]
    ):
        if self._append != -1:
            await self._append_ignore_list(ctx, worksheet, ignore_ids, self._append)
        if self._remove is not None:
            await self._remove_ignore_list(ctx, worksheet, ignore_ids, self._remove)
        if self._download:
            await self._download_ignore_list(ctx, worksheet, ignore_ids)
        if self._show:
            await self._show_ignore_list(ctx, worksheet, ignore_ids)

    @classmethod
    async def _download_ignore_list(
        cls, ctx: Context, worksheet: Worksheet, ignore_ids: List[int]
    ):
        filename = f"ignore_list_{ctx.guild.id}.json"
        logger.debug(f"sheet={worksheet.id}, guild={ctx.guild.id}, json={filename}")
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
                ignore_dict, buffer, default=parse_json, indent=2, ensure_ascii=False
            )
            buffer.seek(0)
            await ctx.send(file=discord.File(buffer, filename))

    @classmethod
    async def _append_ignore_list(
        cls, ctx: Context, worksheet: Worksheet, ignore_ids: List[int], append_id: int
    ):
        logger.debug(f"sheet={worksheet.id}, guild={ctx.guild.id}, user={append_id}")
        member = ctx.guild.get_member(append_id)
        if member is None:
            raise UserNotFoundError(ctx, append_id, guild_id=ctx.guild.id)

        ignore_ids.append(append_id)
        cls._update_cells(worksheet, [str(ignore_id) for ignore_id in ignore_ids])
        await ctx.send(
            f"{member.display_name}[{append_id}] を {ctx.guild.name}[{ctx.guild.id}] の無視リストに追加しました。"
        )

    @classmethod
    async def _remove_ignore_list(
        cls, ctx: Context, worksheet: Worksheet, ignore_ids: List[int], remove: str
    ):
        # intのリストに空の要素が追加できないのでstrにしている
        ignore_list = [str(ignore_id) for ignore_id in ignore_ids]

        if remove.lower() == "all":
            logger.debug(f"sheet={worksheet.id}, guild={ctx.guild.id}, user=all")
            # 要素数は変えずに空文字で埋めて全削除
            ignore_list = ["" for _ in ignore_list]
            output_text = f"{ctx.guild.name}[{ctx.guild.id}] の無視リストから全てのユーザーを除去しました。"
        else:
            try:
                remove_id = int(remove)
            except ValueError:
                raise ExecutionError(ctx, title="️ユーザーIDの指定が正しくありません", remove=remove)

            logger.debug(
                f"sheet={worksheet.id}, guild={ctx.guild.id}, user={remove_id}"
            )
            if remove_id not in ignore_ids:
                raise ExecutionError(ctx, title="️無視リストにユーザーが存在しません", remove=remove_id)

            # 要素数は変えずに空文字で埋めて削除
            ignore_list.remove(str(remove_id))
            ignore_list.append("")
            output_text = f"{ctx.guild.name}[{ctx.guild.id}] の無視リストから user_id={remove_id} を除去しました。"

        cls._update_cells(worksheet, ignore_list)
        await ctx.send(output_text)

    @classmethod
    async def _show_ignore_list(
        cls, ctx: Context, worksheet: Worksheet, ignore_ids: List[int]
    ):
        logger.debug(f"sheet={worksheet.id}, guild={ctx.guild.id}")
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
    def _update_cells(worksheet: Worksheet, values: List[str]):
        cells = worksheet.range(f"A1:A{len(values)}")
        for index, cell in enumerate(cells):
            cell.value = values[index]
        worksheet.update_cells(cells)


class MentionToReactionUsers(Cog, CogHelper):
    def __init__(self, bot: Bot):
        CogHelper.__init__(self, bot)
        self._gspread_client = GSpreadClient()
        self._normal_command: Optional[_NormalCommand] = None
        self._manage_command: Optional[_ManageCommand] = None

    @command()
    async def mention_to_reaction_users(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, ctx: Context, args: Dict[str, str]):
        use_manage = get_bool(args, "manage")
        if use_manage:
            self._manage_command = _ManageCommand()
            self._manage_command.parse_args(ctx, args)
        else:
            self._normal_command = _NormalCommand()
            self._normal_command.parse_args(ctx, args)

    async def _execute(self, ctx: Context):
        # NOTE: シートの取得も1度だけでいいかもしれない
        sheet_id = os.environ["IGNORE_LIST_SHEET_ID"]
        workbook = self._gspread_client.open_by_key(sheet_id)
        sheet_name = str(ctx.guild.id)
        worksheet = get_or_add_worksheet(
            workbook, sheet_name, lambda w, n: w.add_worksheet(n, rows=100, cols=1)
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


def setup(bot: Bot):
    return bot.add_cog(MentionToReactionUsers(bot))
