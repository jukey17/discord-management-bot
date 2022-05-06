import datetime
import re


def parse_args(args):
    parsed = {}
    for arg in args:
        result = re.match(r"(.*)=(.*)", arg)
        if result is None:
            parsed[arg] = "True"
        else:
            parsed[result.group(1)] = result.group(2)

    return parsed


def parse_boolean(dic: dict, key) -> bool:
    return True if key in dic and dic[key].lower() != "false" else False


def parse_or_default(dic: dict, key, default):
    return dic[key] if key in dic else default


def parse_before_after(args: dict):
    before: datetime.datetime = None
    after: datetime.datetime = None
    jst_timezone = datetime.timezone(datetime.timedelta(hours=9), "JST")
    if "before" in args:
        before = (
            datetime.datetime.strptime(args["before"], "%Y-%m-%d")
            .replace(tzinfo=jst_timezone)
        )
    if "after" in args:
        after = (
            datetime.datetime.strptime(args["after"], "%Y-%m-%d")
            .replace(tzinfo=jst_timezone)
        )

    if after is not None and before is not None and after > before:
        raise ValueError("before must be a future than after.")

    return before, after


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat(" ")
    else:
        str(obj)
