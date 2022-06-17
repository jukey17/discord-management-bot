import logging
import os
from enum import Enum
from typing import Dict, List

from discord import Message, Embed
from discord.abc import GuildChannel
from discord.ext.commands import Cog, Bot, command, Context
from discord_ext_commands_coghelper import (
    CogHelper,
    ArgumentError,
    ExecutionError,
    ChannelNotFoundError,
)
from discord_ext_commands_coghelper.utils import get_bool

from gspread.worksheet import Worksheet

from cogs.constant import Constant
from utils.gspread_client import (
    GSpreadClient,
    get_or_add_worksheet,
    duplicate_template_sheet,
)

logger = logging.getLogger(__name__)


class _AlreadyRegisteredError(ExecutionError):
    def __init__(self, ctx: Context, channel: GuildChannel, **kwargs):
        super().__init__(
            ctx, title="既に登録されているチャネルです", channel=channel.mention, **kwargs
        )


class _NotRegisterError(ExecutionError):
    def __init__(self, ctx: Context, channel: GuildChannel, **kwargs):
        super().__init__(ctx, title="登録されていないチャネルです", channel=channel.mention, **kwargs)


class _Constant(Constant):
    SHEET_ID = os.environ["NOTIFY_WHEN_SENT_SHEET_ID"]


class _Mode(Enum):
    REGISTER = 1
    DELETE = 2
    ENABLE = 3
    DISABLE = 4
    LIST = 5


class _Record:
    def __init__(self, user_id: int, channel_id: int, is_valid: bool):
        self._user_id = user_id
        self._channel_id = channel_id
        self._is_valid = is_valid

    def update_is_valid(self, is_valid: bool):
        self._is_valid = is_valid

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def channel_id(self) -> int:
        return self._channel_id

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    def to_list(self) -> List[str]:
        return [str(self._user_id), str(self._channel_id), str(self._is_valid)]

    @classmethod
    def from_dict(cls, dic: dict):
        return cls(int(dic["user_id"]), int(dic["channel_id"]), bool(dic["is_valid"]))


class NotifyWhenSent(Cog, CogHelper):
    def __init__(self, bot: Bot):
        CogHelper.__init__(self, bot)
        self._gspread_client = GSpreadClient()
        self._records: Dict[int, List[_Record]] = {}
        self._mode: _Mode
        self._channel_id: int
        self._list_all: bool

    @command()
    async def notify_when_sent(self, ctx, *args):
        await self.execute(ctx, args)

    @Cog.listener()
    async def on_ready(self):
        workbook = self._gspread_client.open_by_key(_Constant.SHEET_ID)
        for guild in self.bot.guilds:
            sheet_name = str(guild.id)
            worksheet = get_or_add_worksheet(
                workbook, sheet_name, duplicate_template_sheet
            )
            self._get_records(worksheet, guild.id)

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        records = [
            record
            for record in self._records[message.guild.id]
            if record.user_id == message.author.id
            and record.channel_id == message.channel.id
            and record.is_valid
        ]
        for record in records:
            member = message.guild.get_member(record.user_id)
            if not member:
                continue

            logger.debug(f"notify, user={member}, message={message}")
            embed = Embed(
                title=f"#{message.channel.name}({message.guild.name})にメッセージの送信がありました",
                description=f"{message.jump_url}",
            )
            await member.send(embed=embed)

    def _parse_args(self, ctx: Context, args: Dict[str, str]):
        if "register" in args:
            self._mode = _Mode.REGISTER
        elif "delete" in args:
            self._mode = _Mode.DELETE
        elif "enable" in args:
            self._mode = _Mode.ENABLE
        elif "disable" in args:
            self._mode = _Mode.DISABLE
        elif "list" in args:
            self._mode = _Mode.LIST
        else:
            raise ArgumentError(
                ctx, mode="モードを必ず指定してください(register/delete/enable/disable/list)"
            )

        if self._mode == _Mode.LIST:
            self._list_all = get_bool(args, "all", False)
            return

        if "channel" not in args:
            raise ArgumentError(ctx, channel="対象となるチャンネルを指定してください")
        try:
            self._channel_id = int(args["channel"])
        except ValueError:
            raise ArgumentError(ctx, channel="チャンネルIDの指定が正しくありません")

    async def _execute(self, ctx: Context):
        if not ctx.guild:
            raise ExecutionError(ctx, title="このBOTが参加しているサーバー内で実行してください")

        if self._mode != _Mode.LIST and not ctx.guild.get_channel(self._channel_id):
            raise ChannelNotFoundError(ctx, self._channel_id)

        workbook = self._gspread_client.open_by_key(_Constant.SHEET_ID)
        sheet_name = str(ctx.guild.id)
        worksheet = get_or_add_worksheet(workbook, sheet_name, duplicate_template_sheet)
        self._get_records(worksheet, ctx.guild.id)

        if self._mode == _Mode.REGISTER:
            await self._execute_register(ctx)
        elif self._mode == _Mode.DELETE:
            await self._execute_delete(ctx)
        elif self._mode == _Mode.ENABLE:
            await self._execute_enable(ctx)
        elif self._mode == _Mode.DISABLE:
            await self._execute_disable(ctx)
        elif self._mode == _Mode.LIST:
            await self._execute_list(ctx)

        self._set_records(worksheet, ctx.guild.id)

    async def _execute_register(self, ctx: Context):
        channel = ctx.guild.get_channel(self._channel_id)
        if self._find_record(ctx.guild.id, ctx.author.id, self._channel_id):
            raise _AlreadyRegisteredError(ctx, channel)
        else:
            record = _Record(ctx.author.id, self._channel_id, True)
            self._records[ctx.guild.id].append(record)
            logger.debug(f"record={record}")
            await ctx.send(f"{channel.mention} を通知対象として登録しました")

    async def _execute_delete(self, ctx: Context):
        channel = ctx.guild.get_channel(self._channel_id)
        record = self._find_record(ctx.guild.id, ctx.author.id, self._channel_id)
        if not record:
            raise _NotRegisterError(ctx, channel)
        else:
            self._records[ctx.guild.id].remove(record)
            logger.debug(f"record={record}")
            await ctx.send(f"{channel.mention} の通知設定を削除しました")

    async def _execute_enable(self, ctx: Context):
        channel = ctx.guild.get_channel(self._channel_id)
        record = self._find_record(ctx.guild.id, ctx.author.id, self._channel_id)
        if not record:
            raise _NotRegisterError(ctx, channel)
        else:
            logger.debug(f"record={record}")
            record.update_is_valid(True)
            await ctx.send(f"{channel.mention} の通知設定を有効にしました")

    async def _execute_disable(self, ctx: Context):
        channel = ctx.guild.get_channel(self._channel_id)
        record = self._find_record(ctx.guild.id, ctx.author.id, self._channel_id)
        if not record:
            raise _NotRegisterError(ctx, channel)
        else:
            logger.debug(f"record={record}")
            record.update_is_valid(False)
            await ctx.send(f"{channel.mention} の通知設定を無効にしました")

    async def _execute_list(self, ctx: Context):
        embed = Embed(
            title=f"{ctx.author.display_name} の通知一覧",
            description=f"サーバー名: {ctx.guild.name}",
        )
        for record in self._records[ctx.guild.id]:
            if not self._list_all and record.user_id != ctx.author.id:
                continue
            channel = ctx.guild.get_channel(record.channel_id)
            state = "有効" if record.is_valid else "無効"
            embed.add_field(
                name=f"チャンネル名: {channel.name}",
                value=f"通知状態: {state}",
                inline=False,
            )
        await ctx.send(embed=embed)

    def _find_record(self, guild_id: int, user_id: int, channel_id: int) -> _Record:
        records = [
            record
            for record in self._records[guild_id]
            if int(record.user_id) == user_id and int(record.channel_id) == channel_id
        ]
        return records[0] if len(records) > 0 else None

    def _set_records(self, worksheet: Worksheet, guild_id: int):
        rows = worksheet.get_all_records()
        worksheet.delete_rows(2, len(rows) + 2)
        worksheet.insert_rows(
            [record.to_list() for record in self._records[guild_id]], 2
        )

    def _get_records(self, worksheet: Worksheet, guild_id: int):
        self._records[guild_id] = [
            _Record.from_dict(record) for record in worksheet.get_all_records()
        ]


def setup(bot: Bot):
    return bot.add_cog(NotifyWhenSent(bot))
