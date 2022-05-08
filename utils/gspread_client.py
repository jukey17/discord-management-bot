import os
from typing import Callable

import gspread
from google.oauth2.service_account import Credentials

from utils.singleton import Singleton


def get_or_add_worksheet(
    workbook: gspread.Spreadsheet,
    name: str,
    add_func: Callable[[gspread.Spreadsheet, str], gspread.Worksheet] = None,
) -> gspread.Worksheet:
    try:
        return workbook.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        if add_func is None:
            return workbook.add_worksheet(name, rows=100, cols=100)
        else:
            return add_func(workbook, name)


class GSpreadClient(Singleton):
    def __init__(self):
        # 認証は生成時に一度だけ
        # TODO: 起動し続けていて認証エラーが出るようだったらそのときに対策を考える
        credentials = Credentials.from_service_account_file(
            os.environ["GOOGLE_CREDENTIALS_FILE"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._gspread_client = gspread.authorize(credentials)

    def open_by_key(self, key: str) -> gspread.Spreadsheet:
        return self._gspread_client.open_by_key(key)
