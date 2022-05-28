import datetime
import logging
import os
from typing import Dict, List

import discord.ext
import discord.ext.commands
import discord.ext.tasks
import gspread.utils
import gspread.worksheet

import utils.misc
import utils.discord
import cogs.constant
from cogs.cog import CogBase
from utils.gspread_client import GSpreadClient


logger = logging.getLogger(__name__)


class _Constant(cogs.constant.Constant):
    SHEET_ID = os.environ.get("LOGGING_MESSAGES_SHEET_ID", "")
    INTERVAL_TIME = datetime.datetime.strptime(
        os.environ.get("MESSAGE_COUNT_INTERVAL_TIME", "00:00:00"),
        cogs.constant.Constant.TIME_FORMAT,
    )


class LoggingMessages(discord.ext.commands.Cog, CogBase):
    def __init__(self, bot: discord.ext.commands.Bot):
        CogBase.__init__(self, bot)
        self._update_modes: List[str]
        self._gspread_client = GSpreadClient()
        self._interval_triggered: Dict[int, bool] = {}

    @discord.ext.commands.command()
    async def logging_messages(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: Dict[str, str]):
        self._update_modes = utils.misc.get_array(
            args, "update", ",", lambda value: value, []
        )

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        workbook = self._gspread_client.open_by_key(_Constant.SHEET_ID)

        for mode in self._update_modes:
            if mode == "channel":
                self._update_channel_sheet(workbook, ctx.guild)
            elif mode == "member":
                self._update_member_sheet(workbook, ctx.guild)

    @staticmethod
    def _update_channel_sheet(workbook: gspread.Spreadsheet, guild: discord.Guild):
        def append_header(h: gspread.worksheet.Worksheet):
            h.append_row(["id", "name", "type", "created_at"])

        def add_sheet(w: gspread.Spreadsheet, n: str) -> gspread.worksheet.Worksheet:
            h = w.add_worksheet(n, 100, 2)
            append_header(h)
            return h

        sheet = utils.gspread_client.get_or_add_worksheet(
            workbook, f"{guild.id}.channel", add_sheet
        )

        records = sheet.get_all_records()
        logger.debug(f"prev records: {records}")

        # 現在のサーバー内のチャンネル情報を取得
        records = []
        for channel in guild.channels:
            if all([channel.id != int(record["id"]) for record in records]):
                created_at = (
                    channel.created_at.replace(tzinfo=datetime.timezone.utc)
                    .astimezone(_Constant.JST)
                    .strftime(_Constant.DATE_FORMAT)
                )
                record = dict(
                    id=str(channel.id),
                    name=channel.name,
                    type=str(channel.type),
                    created_at=created_at,
                )
                records.append(record)

        # 毎回新しいレコードに総置き換え
        sheet.clear()
        append_header(sheet)
        values = [list(record.values()) for record in records]
        logger.debug(f"append records: {values}")
        sheet.append_rows(
            values=values,
            value_input_option=gspread.utils.ValueInputOption.raw,
        )

    @staticmethod
    def _update_member_sheet(workbook: gspread.Spreadsheet, guild: discord.Guild):
        def append_header(h: gspread.worksheet.Worksheet):
            h.append_row(["id", "name", "nick", "joined_at"])

        def add_sheet(w: gspread.Spreadsheet, n: str) -> gspread.worksheet.Worksheet:
            h = w.add_worksheet(n, 100, 2)
            append_header(h)
            return h

        sheet = utils.gspread_client.get_or_add_worksheet(
            workbook, f"{guild.id}.member", add_sheet
        )

        records = sheet.get_all_records()
        logger.debug(f"prev records: {records}")

        # 現在のサーバー内のメンバー情報を取得
        records = []
        for member in guild.members:
            if all([member.id != int(record["id"]) for record in records]):
                if member.joined_at:
                    joined_at = (
                        member.joined_at.replace(tzinfo=datetime.timezone.utc)
                        .astimezone(_Constant.JST)
                        .strftime(_Constant.DATE_FORMAT)
                    )
                else:
                    joined_at = "UNKNOWN"
                record = dict(
                    id=str(member.id),
                    name=member.name,
                    nick=member.nick,
                    joined_at=joined_at,
                )
                records.append(record)

        # 毎回新しいレコードに総置き換え
        sheet.clear()
        append_header(sheet)
        values = [list(record.values()) for record in records]
        logger.debug(f"append records: {values}")
        sheet.append_rows(
            values=values,
            value_input_option=gspread.utils.ValueInputOption.raw,
        )


def setup(bot: discord.ext.commands.Bot):
    return bot.add_cog(LoggingMessages(bot))
