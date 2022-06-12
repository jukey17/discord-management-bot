import datetime
import re


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
