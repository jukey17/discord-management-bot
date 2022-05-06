import contextlib
import io
import json
import os
from abc import ABC

import discord
import discord.ext
import gspread
from google.oauth2.service_account import Credentials

from commands.command import CommandBase
from utils.discord import find_channel, find_no_reaction_users, find_reaction_users
from utils.misc import parse_boolean, parse_or_default, parse_json


class _NormalCommand:
    def __init__(self):
        self._channel: discord.abc.GuildChannel = None
        self._message: discord.Message = None
        self._message_id: int = None
        self._reaction_emoji: str = None
        self._use_ignore_list: bool = False
        self._ignore_ids: list = None

    def parse_args(self, args: dict):
        self._use_ignore_list = parse_boolean(args, "ignore_list")
        self._message_id = int(args["message"])
        self._reaction_emoji = args["reaction"]

    async def prepare(
        self, ctx: discord.ext.commands.context.Context, ignore_ids: list
    ):
        self._channel, self._message = await find_channel(ctx.guild, self._message_id)
        print(
            f"fetch message: channel={self._channel.name}, message={self._message.content}"
        )
        self._ignore_ids = ignore_ids

    async def execute(self, ctx: discord.ext.commands.context.Context):
        if self._channel is None:
            raise ValueError(f"not found channel, message_id={self._message_id}")

        if self._message is None:
            raise ValueError(f"not found message, id={self._message_id}")

        if self._reaction_emoji.lower() == "none":
            targets = [
                member
                for member in self._channel.members
                if not member.bot
                and member.id != self._message.author.id
                and member.id not in self._ignore_ids
            ]
            print(
                f"find no reaction users: target={[member.display_name for member in targets]}"
            )
            result = await find_no_reaction_users(self._message, targets)
        elif self._reaction_emoji.lower() == "all":
            print("all reaction users")
            result = []
            for reaction in self._message.reactions:
                users = [user async for user in reaction.users()]
                result.extend(users)
        else:
            print(f"find reaction users: target={self._reaction_emoji}")
            result = await find_reaction_users(
                self._message, self._ignore_ids, self._reaction_emoji
            )

        if len(result) > 0:
            output_text = ", ".join([member.mention for member in list(set(result))])
        else:
            output_text = "none!"

        print(f"send: {output_text}")
        await ctx.send(output_text)


class _ManageCommand:
    def __init__(self):
        self._download = False
        self._append = None
        self._remove = None
        self._show = False
        self._use_ignore_list = False
        self._worksheet = None
        self._ignore_ids = None

    def parse_args(self, args: dict):
        self._download = parse_boolean(args, "download")
        self._append = parse_or_default(args, "append", None)
        self._remove = parse_or_default(args, "remove", None)
        self._show = parse_boolean(args, "show")
        self._use_ignore_list = parse_boolean(args, "ignore_list")

    async def prepare(
        self,
        ctx: discord.ext.commands.context.Context,
        worksheet: gspread.worksheet.Worksheet,
        ignore_ids: list,
    ):
        # NOTE: シートの取得も1度だけでいいかもしれない
        self._worksheet = worksheet
        self._ignore_ids = ignore_ids

    async def execute(self, ctx: discord.ext.commands.context.Context):
        if self._use_ignore_list:
            await self._manage_ignore_list(ctx)

    async def _manage_ignore_list(self, ctx: discord.ext.commands.context.Context):
        ignore_users = [
            ctx.guild.get_member(int(user_id)) for user_id in self._ignore_ids
        ]

        if self._download:
            filename = f"ignore_list_{ctx.guild.id}.json"
            print(
                f"download ignore_list: sheet_id={self._sheet_id}, guild={ctx.guild.id}-> {filename}"
            )
            ignore_dict = [
                dict(id=user.id, name=user.name, display_name=user.display_name)
                for user in ignore_users
            ]
            with contextlib.closing(io.StringIO()) as buffer:
                json.dump(
                    ignore_dict,
                    buffer,
                    default=parse_json,
                    indent=2,
                    ensure_ascii=False,
                )
                buffer.seek(0)
                await ctx.send(file=discord.File(buffer, filename))

        if self._append is not None:
            append_id = int(self._append)
            print(
                f"append ignore_list: sheet_id={self._sheet_id}, guild={ctx.guild.id}, user={append_id}"
            )
            if ctx.guild.get_member(append_id) is None:
                await ctx.send(f"not found user: id={append_id}")
                return

            self._ignore_ids.append(append_id)
            update_cells = self._worksheet.range(f"A1:A{len(self._ignore_ids)}")
            for i, cell in enumerate(update_cells):
                cell.value = self._ignore_ids[i]
            self._worksheet.update_cells(update_cells)
            await ctx.send("completed append ignore_list!")

        if self._remove is not None:
            remove_id = int(self._remove)
            print(
                f"remove ignore_list: sheet_id={self._sheet_id}, guild={ctx.guild.id}, user={remove_id}"
            )
            if remove_id not in self._ignore_ids:
                await ctx.send(f"not contains ignore_list: user_id={remove_id}")
                return
            self._ignore_ids.remove(remove_id)
            self._ignore_ids.append("")
            update_cells = self._worksheet.range(f"A1:A{len(self._ignore_ids)}")
            for i, cell in enumerate(update_cells):
                cell.value = self._ignore_ids[i]
            self._worksheet.update_cells(update_cells)
            await ctx.send("completed remove ignore_list!")

        if self._show:
            print(f"show ignore_list: sheet_id={self._sheet_id}, guild={ctx.guild.id}")
            await ctx.send(
                "\n".join([f"{user.display_name} {user.id}" for user in ignore_users])
            )


class MentionToReactionUsersCommand(CommandBase, ABC):
    def __init__(self):
        CommandBase.__init__(self)

        # 認証は生成時に一度だけ
        # TODO: 起動し続けてて認証エラーが出てから対策を考える
        credentials = Credentials.from_service_account_file(
            os.environ["GOOGLE_CREDENTIALS_FILE"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._gspread_client = gspread.authorize(credentials)
        self._normal_command: _NormalCommand = None
        self._manage_command: _ManageCommand = None

    def _parse_args(self, args: dict):
        self._use_ignore_list = parse_boolean(args, "ignore_list")
        use_manage = parse_boolean(args, "manage")
        if use_manage:
            self._manage_command = _ManageCommand()
            self._manage_command.parse_args(args)
        else:
            self._normal_command = _NormalCommand()
            self._normal_command.parse_args(args)

    async def _prepare(self, ctx: discord.ext.commands.context.Context):
        # NOTE: シートの取得も1度だけでいいかもしれない
        sheet_id = os.environ["IGNORE_LIST_SHEET_ID"]
        workbook = self._gspread_client.open_by_key(sheet_id)
        worksheet = workbook.worksheet(str(ctx.guild.id))
        ignore_list = worksheet.col_values(1)
        ignore_ids = [int(ignore_id) for ignore_id in ignore_list]
        print(f"fetch ignore_ids: ignore_ids={ignore_ids}")

        if self._manage_command is not None:
            await self._manage_command.prepare(ctx, worksheet, ignore_ids)

        if self._normal_command is not None:
            await self._normal_command.prepare(ctx, ignore_ids)

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        if self._manage_command is not None:
            await self._manage_command.execute(ctx)

        if self._normal_command is not None:
            await self._normal_command.execute(ctx)
