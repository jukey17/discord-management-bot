import datetime
import re
from typing import Optional, List, Callable, Any, Dict

from utils.constant import Constant


def parse_args(args) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = "True"
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def get_boolean(dic: Dict[str, str], key: str, default: bool = False) -> bool:
    if key not in dic:
        return default
    return True if dic[key].lower() != "false" else False


def get_array(
    dic: Dict[str, str],
    key: str,
    delimiter: str,
    func: Callable[[str], Any],
    default: List[Any],
) -> List[Any]:
    if key not in dic:
        return default
    return [func(value) for value in dic[key].split(delimiter)]


def get_before_after_jst(
    args: Dict[str, str], to_aware: bool = True
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


def back_from_modified_datetime(date_str: str, time_str: str) -> datetime.datetime:
    date_match = re.match(
        r"^(\d{4})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])$", date_str
    )
    # 47:59:59まで取れるようにする
    time_match = re.match(r"^([0-3]?\d|4[0-7]):([0-5]?\d):([0-5]?\d)$", time_str)

    if not date_match or len(date_match.groups()) < 3:
        raise ValueError(f"not parse date={date_str}")
    if not time_match or len(time_match.groups()) < 3:
        raise ValueError(f"not parse time={time_str}")

    year = int(date_match.groups()[0])
    month = int(date_match.groups()[1])
    day = int(date_match.groups()[2])
    hour = int(time_match.groups()[0])
    minute = int(time_match.groups()[1])
    second = int(time_match.groups()[2])

    date = datetime.date(year, month, day)
    # 24時間以上の場合はdatetimeが認識できる範囲に戻す
    if hour >= 24:
        hour -= 24
        date += datetime.timedelta(days=1)

    return datetime.datetime(date.year, date.month, date.day, hour, minute, second)


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        # 正式な区切り文字はTらしいが素人目では見にくいのでとりあえず半角スペースにしている
        return obj.isoformat(" ")
    else:
        str(obj)
