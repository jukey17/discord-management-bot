import contextlib
import io
import json
import os
from typing import Optional, Dict

import discord.ext.commands
import gspread
import dispander.module

import utils.misc
from cogs.cog import CogBase
from utils.discord import find_channel, find_reaction_users, find_no_reaction_users
from utils.gspread_client import GSpreadClient


class _NormalCommand:
    def __init__(self, bot):
        self.bot = bot
        self._message_id: Optional[int] = None
        self._reaction_emoji: Optional[str] = None
        self._use_ignore_list: Optional[bool] = False

    def parse_args(self, args: dict):
        # 通常モードではignore_listはデフォルトで利用する
        self._use_ignore_list = utils.misc.get_boolean(args, "ignore_list", True)
        self._message_id = int(args["message"])
        self._reaction_emoji = args["reaction"]

    async def execute(
        self, ctx: discord.ext.commands.context.Context, ignore_ids: list
    ):
        # 無視リストを使わない
        if not self._use_ignore_list:
            ignore_ids.clear()

        channel, message = await find_channel(ctx.guild, self._message_id)
        print(f"fetch message: channel={channel.name}, message={message.content}")

        if channel is None:
            raise ValueError(f"not found channel, message_id={self._message_id}")

        if not isinstance(channel, discord.TextChannel):
            raise TypeError(f"{type(channel)} is not TextChannel.")

        if message is None:
            raise ValueError(f"not found message, id={self._message_id}")

        # BOTではない かつ メッセージの投稿者ではない かつ 無視リストに含まれていない
        def filter_users(u: list, m: discord.Message) -> list:
            return [
                user
                for user in u
                if not user.bot and user.id != m.author.id and user.id not in ignore_ids
            ]

        if self._reaction_emoji.lower() == "none":
            targets = filter_users(channel.members, message)
            print(
                f"find no reaction users: target={[member.display_name for member in targets]}"
            )
            result = await find_no_reaction_users(message, targets)
        elif self._reaction_emoji.lower() == "all":
            print("all reaction users")
            result = []
            for reaction in message.reactions:
                users = [user async for user in reaction.users()]
                result.extend(filter_users(users, message))
        else:
            print(f"find reaction users: target={self._reaction_emoji}")
            targets = await find_reaction_users(message, self._reaction_emoji)
            result = filter_users(targets, message)

        if len(result) > 0:
            # 重複は除く
            output_text = ", ".join([user.mention for user in list(set(result))])
        else:
            output_text = "none!"

        print(f"send: {output_text}")
        await ctx.send(output_text)

        # copy and modify from dispander method
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

    def parse_args(self, args: dict):
        self._use_ignore_list = utils.misc.get_boolean(args, "ignore_list")
        self._download = utils.misc.get_boolean(args, "download")
        self._append = args.get("append", None)
        self._remove = args.get("remove", None)
        self._show = utils.misc.get_boolean(args, "show")

    async def execute(
        self,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: list,
    ):
        if self._use_ignore_list:
            await self._manage_ignore_list(ctx, worksheet, ignore_ids)

    async def _manage_ignore_list(
        self,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: list,
    ):
        # 既にサーバーから抜けている可能性がある
        ignore_users = [
            (user_id, ctx.guild.get_member(user_id)) for user_id in ignore_ids
        ]

        def update_cells(w: gspread.worksheet.Worksheet, il: list):
            cs = w.range(f"A1:A{len(il)}")
            for i, c in enumerate(cs):
                c.value = str(il[i])
            w.update_cells(cs)

        if self._download:
            filename = f"ignore_list_{ctx.guild.id}.json"
            print(
                f"download ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}-> {filename}"
            )
            ignore_dict = []
            for user_id, user in ignore_users:
                if user is None:
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

        if self._append is not None:
            append_id = int(self._append)
            print(
                f"append ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, user={append_id}"
            )
            member = ctx.guild.get_member(append_id)
            if member is None:
                await ctx.send(f"not found user: id={append_id}")
                return

            ignore_ids.append(append_id)
            update_cells(worksheet, ignore_ids)
            await ctx.send(f"append {member.display_name} {append_id} to ignore_list.")

        if self._remove is not None:
            if self._remove.lower() == "all":
                ignore_ids.clear()
                output_text = "remove all from ignore_list."
            else:
                remove_id = int(self._remove)
                print(
                    f"remove ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}, user={remove_id}"
                )
                if remove_id not in ignore_ids:
                    await ctx.send(f"not contains ignore_list: user_id={remove_id}")
                    return
                ignore_ids.remove(remove_id)
                ignore_ids.append("")
                output_text = f"remove {remove_id} from ignore_list."
            update_cells(worksheet, ignore_ids)
            await ctx.send(output_text)

        if self._show:
            print(f"show ignore_list: sheet_id={worksheet.id}, guild={ctx.guild.id}")
            outputs = [f"show ignore_list: guild={ctx.guild.name}"]
            if len(ignore_ids) == 0:
                outputs.append("none.")
            for user_id, user in ignore_users:
                if user is None:
                    outputs.append(f"[Not Found] {user_id}")
                else:
                    outputs.append(f"{user.display_name} {user.id}")

            await ctx.send("\n".join(outputs))


class MentionToReactionUsers(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self)
        self.bot = bot
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
        worksheet: Optional[gspread.Worksheet] = None
        try:
            worksheet = workbook.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"{sheet_name} does not exist, so add a new one. ")
            worksheet = workbook.add_worksheet(sheet_name, rows=100, cols=1)
        finally:
            ignore_list = worksheet.col_values(1)
            ignore_ids = [int(ignore_id) for ignore_id in ignore_list]
        print(f"fetch ignore_ids: ignore_ids={ignore_ids}")

        if self._manage_command is not None:
            await self._manage_command.execute(ctx, worksheet, ignore_ids)
            self._manage_command = None

        if self._normal_command is not None:
            await self._normal_command.execute(ctx, ignore_ids)
            self._normal_command = None


def setup(bot):
    return bot.add_cog(MentionToReactionUsers(bot))
