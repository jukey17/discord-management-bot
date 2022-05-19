import datetime
import re
from typing import Optional

from utils.constant import Constant


def parse_args(args):
    parsed = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = "True"
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def get_boolean(dic: dict, key, default: bool = False) -> bool:
    if key not in dic:
        return default
    return True if dic[key].lower() != "false" else False


def get_before_after_jst(
    args: dict, to_aware: bool = True
) -> (datetime.datetime, datetime.datetime):
    before: Optional[datetime.datetime] = None
    after: Optional[datetime.datetime] = None
    if "before" in args:
        before = datetime.datetime.strptime(args["before"], "%Y-%m-%d")
        if to_aware:
            before = before.replace(tzinfo=Constant.JST)
    if "after" in args:
        after = datetime.datetime.strptime(args["after"], "%Y-%m-%d")
        if to_aware:
            after = after.replace(tzinfo=Constant.JST)

    if after is not None and before is not None and after > before:
        raise ValueError("before must be a future than after.")

    return before, after


def get_modified_datetime(
    target: datetime.datetime, when_date_changed: datetime.time
) -> (int, int, int, int, int, int, int):

    # 対象の日時が日付変更タイミングを超えていたら
    if when_date_changed <= target.time():
        # そのまま使う
        return (
            target.year,
            target.month,
            target.day,
            target.hour,
            target.minute,
            target.second,
            target.microsecond,
        )

    # 日付を一日戻して時間を24時間表記にする
    modified_date = target.date() - datetime.timedelta(days=1)
    return (
        modified_date.year,
        modified_date.month,
        modified_date.day,
        24 + target.hour,
        target.minute,
        target.second,
        target.microsecond,
    )


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        # 正式な区切り文字はTらしいが素人目では見にくいのでとりあえず半角スペースにしている
        return obj.isoformat(" ")
    else:
        str(obj)
