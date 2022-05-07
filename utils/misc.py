import datetime
import re
from typing import Optional


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


def get_before_after_jst(args: dict):
    before: Optional[datetime.datetime] = None
    after: Optional[datetime.datetime] = None
    jst = datetime.timezone(datetime.timedelta(hours=9), "JST")
    if "before" in args:
        before = datetime.datetime.strptime(args["before"], "%Y-%m-%d").replace(
            tzinfo=jst
        )
    if "after" in args:
        after = datetime.datetime.strptime(args["after"], "%Y-%m-%d").replace(
            tzinfo=jst
        )

    if after is not None and before is not None and after > before:
        raise ValueError("before must be a future than after.")

    return before, after


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        # 正式な区切り文字はTらしいが素人目では見にくいのでとりあえず半角スペースにしている
        return obj.isoformat(" ")
    else:
        str(obj)
