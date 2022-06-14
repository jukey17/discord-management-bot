from utils import constant


class Constant(constant.Constant):
    DATE_FORMAT_SLASH = "%Y/%m/%d"
    DATE_FORMAT_HYPHEN = "%Y-%m-%d"
    DATE_FORMATS = [DATE_FORMAT_SLASH, DATE_FORMAT_HYPHEN]
    TIME_FORMAT = "%H:%M:%S"
