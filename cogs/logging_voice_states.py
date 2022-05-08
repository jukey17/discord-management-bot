import contextlib
import datetime
import io
import json
import os
from typing import Optional

import discord
import gspread
from discord.ext import commands

from cogs.cog import CogBase
from utils.gspread_client import GSpreadClient, get_or_add_worksheet
from utils.misc import get_before_after_jst, parse_json

TIME_FORMAT = "%Y/%m/%d %H:%M:%S.%f"


def _duplicate_template_sheet(
    workbook: gspread.Spreadsheet, name: str
) -> gspread.Worksheet:
    print(f"{name} does not exist, so add a new one. ")
    template = workbook.worksheet("template")
    return template.duplicate(new_sheet_name=name)


class LoggingVoiceStates(commands.Cog, CogBase):
    def __init__(self, bot):
        CogBase.__init__(self)
        self.bot = bot
        self._gspread_client = GSpreadClient()
        self._count: Optional[str] = None
        self._user_id: Optional[int] = None
        self._download: str
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    @commands.command()
    async def logging_voice_states(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: dict):
        self._count = args.get("count", None)
        self._user_id = args.get("user", None)
        self._before, self._after = get_before_after_jst(args, False)

    async def _execute(self, ctx: discord.ext.commands.context.Context):
        if self._count is not None:
            await self._execute_count(ctx)

    async def _execute_count(self, ctx: discord.ext.commands.context.Context):
        sheet_id = os.environ["LOGGING_VOICE_STATES_SHEET_ID"]
        workbook = self._gspread_client.open_by_key(sheet_id)
        sheet_name = str(ctx.guild.id)
        worksheet = get_or_add_worksheet(
            workbook, sheet_name, _duplicate_template_sheet
        )

        records = []
        for record in worksheet.get_all_records():
            time = datetime.datetime.strptime(
                record["time"],
                TIME_FORMAT,
            )
            if self._after is not None and self._before is not None:
                if self._after < time < self._before:
                    records.append(record)
            elif self._after is None and self._before is not None:
                if time < self._before:
                    records.append(record)
            elif self._after is not None and self._before is None:
                if self._after < time:
                    records.append(record)
            else:
                records.append(record)

        targets = []
        if self._user_id is not None:
            user = ctx.guild.get_member(int(self._user_id))
            if user is None:
                await ctx.send(f"not found user: id={self._user_id}")
                return
            targets.append(user)
        else:
            targets.extend([member for member in ctx.guild.members if not member.bot])

        results = []
        for target in targets:
            matched = [
                record
                for record in records
                if record["user_id"] == target.id and self._count in record["state"]
            ]

            results.append(
                {
                    "user": {"id": target.id, "name": target.display_name},
                    "state": self._count,
                    "count": len(matched),
                }
            )

        before_str = "None" if self._before is None else self._before.strftime("%Y%m%d")
        after_str = "None" if self._after is None else self._after.strftime("%Y%m%d")

        filename = f"logging_voice_states_count_{self._count}_{before_str}_{after_str}"
        with contextlib.closing(io.StringIO()) as buffer:
            json.dump(
                results,
                buffer,
                default=parse_json,
                indent=2,
                ensure_ascii=False,
            )
            buffer.seek(0)
            await ctx.send(file=discord.File(buffer, f"{filename}.json"))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        sheet_id = os.environ["LOGGING_VOICE_STATES_SHEET_ID"]
        workbook = self._gspread_client.open_by_key(sheet_id)
        sheet_name = str(member.guild.id)
        worksheet = get_or_add_worksheet(
            workbook, sheet_name, _duplicate_template_sheet
        )
        record = {
            "time": datetime.datetime.now().strftime(TIME_FORMAT),
            "user_name": member.display_name,
            "user_id": str(member.id),
        }
        state = []
        if before.channel is None and after.channel is not None:
            record["channel_name"] = after.channel.name
            record["channel_id"] = str(after.channel.id)
            state.append("join")
            # 接続前からmute/deaf状態にしているケースがあるため接続時にもチェックする
            if before.self_mute:
                state.append("mute_on")
            if before.self_deaf:
                state.append("deaf_on")
        if before.channel is not None and after.channel is None:
            record["channel_name"] = before.channel.name
            record["channel_id"] = str(before.channel.id)
            state.append("leave")
            # 切断時に配信していたら強制的に終了するので状態も終了とみなす ※mute/deafは継続するのでスルー
            if before.self_stream:
                state.append("stream_end")
            if before.self_video:
                state.append("video_off")
        if before.channel is not None and after.channel is not None:
            record["channel_name"] = after.channel.name
            record["channel_id"] = str(after.channel.id)
        if not before.self_mute and after.self_mute:
            state.append("mute_on")
        if before.self_mute and not after.self_mute:
            state.append("mute_off")
        if not before.self_deaf and after.self_deaf:
            state.append("deaf_on")
        if before.self_deaf and not after.self_deaf:
            state.append("deaf_off")
        if not before.self_stream and after.self_stream:
            state.append("stream_begin")
        if before.self_stream and not after.self_stream:
            state.append("stream_end")
        if not before.self_video and after.self_video:
            state.append("video_on")
        if before.self_video and not after.self_video:
            state.append("video_off")

        record["state"] = ",".join(sorted(set(state), key=state.index))
        worksheet.append_row(list(record.values()))
        print(f"append record: {record}")


def setup(bot):
    return bot.add_cog(LoggingVoiceStates(bot))
