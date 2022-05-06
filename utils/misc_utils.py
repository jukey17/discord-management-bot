import datetime


def parse_before_after(args: dict):
    before: datetime.datetime = None
    after: datetime.datetime = None
    jst_timezone = datetime.timezone(datetime.timedelta(hours=9), "JST")
    if "before" in args:
        before = (
            datetime.datetime.strptime(args["before"], "%Y-%m-%d")
            .replace(tzinfo=jst_timezone)
            .astimezone(datetime.timezone.utc)
            .replace(tzinfo=None)
        )
    if "after" in args:
        after = (
            datetime.datetime.strptime(args["after"], "%Y-%m-%d")
            .replace(tzinfo=jst_timezone)
            .astimezone(datetime.timezone.utc)
            .replace(tzinfo=None)
        )

    if after is not None and before is not None and after > before:
        raise ValueError("before must be a future than after.")

    return before, after


def parse_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat(" ")
    else:
        str(obj)
