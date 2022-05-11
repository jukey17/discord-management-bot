import contextlib
import datetime
import io
import json
import os
from typing import Optional, List

import discord
import gspread
from discord.ext import commands

from cogs.cog import CogBase
from utils.gspread_client import GSpreadClient, get_or_add_worksheet
from utils.misc import get_before_after_jst, parse_json

DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H:%M:%S.%f"
JST = datetime.timezone(datetime.timedelta(hours=9), "JST")


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
        self._user_ids: List[int]
        self._channel_ids: List[int]
        self._before: Optional[datetime.datetime] = None
        self._after: Optional[datetime.datetime] = None

    @commands.command()
    async def logging_voice_states(self, ctx, *args):
        await self.execute(ctx, args)

    def _parse_args(self, args: dict):
        self._count = args.get("count", None)
        self._user_id = args.get("user", None)
        self._user_ids = (
            [int(user_id) for user_id in args["user"].split(",")]
            if "user" in args
            else []
        )
        self._channel_ids = (
            [int(channel_id) for channel_id in args["channel"].split(",")]
            if "channel" in args
            else []
        )
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
            date = datetime.datetime.strptime(
                record["date"],
                DATE_FORMAT,
            )
            time = datetime.datetime.strptime(
                record["time"],
                TIME_FORMAT,
            )
            dt = datetime.datetime(
                year=date.year,
                month=date.month,
                day=date.day,
                hour=time.hour,
                minute=time.hour,
                second=time.second,
                microsecond=time.microsecond,
            )
            if self._after is not None and self._before is not None:
                if self._after < dt < self._before:
                    records.append(record)
            elif self._after is None and self._before is not None:
                if dt < self._before:
                    records.append(record)
            elif self._after is not None and self._before is None:
                if self._after < dt:
                    records.append(record)
            else:
                records.append(record)

        if len(self._user_ids) > 0:
            # ユーザーIDの指定がある→指定のユーザーだけ
            users = [m for m in ctx.guild.members if m.id in self._user_ids]
        else:
            # ユーザーIDの指定がない→BOT以外のサーバー参加ユーザー
            users = [m for m in ctx.guild.members if not m.bot]

        if len(self._channel_ids) > 0:
            # チャンネルIDの指定がある→指定のチャンネルだけ
            channels = [c for c in ctx.guild.channels if c.id in self._channel_ids]
        else:
            # チャンネルIDの指定がない→サーバーのボイスチャンネル
            channels = [
                c for c in ctx.guild.channels if isinstance(c, discord.VoiceChannel)
            ]

        results = []
        for user in users:
            for channel in channels:
                matched = [
                    record
                    for record in records
                    if record["user_id"] == user.id
                    and record["channel_id"] == channel.id
                    and self._count in record["state"]
                ]
                results.append(
                    {
                        "user": {"id": user.id, "name": user.display_name},
                        "channel": {"id": channel.id, "name": channel.name},
                        "state": self._count,
                        "count": len(matched),
                    }
                )

        if self._before is None:
            before_str = (
                datetime.datetime.now().replace(tzinfo=JST).strftime("%Y/%m/%d")
            )
        else:
            before_str = self._before.strftime("%Y/%m/%d")
        if self._after is None:
            after_str = (
                ctx.guild.created_at.replace(tzinfo=datetime.timezone.utc)
                .astimezone(JST)
                .strftime("%Y/%m/%d")
            )
        else:
            after_str = self._after.strftime("%Y/%m/%d")

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

        now = datetime.datetime.now(tz=JST)
        record = {
            "date": now.date().strftime(DATE_FORMAT),
            "time": now.time().strftime(TIME_FORMAT),
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
        worksheet.append_row(list(record.values()), value_input_option="USER_ENTERED")
        print(f"append record: {record}")


def setup(bot):
    return bot.add_cog(LoggingVoiceStates(bot))
