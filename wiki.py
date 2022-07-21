import time
import threading
from telegram.ext import *
from telegram import *
from log import logger
import dokuwiki
import bs4
import re


class MessageKeyboardWIKI:
    def __init__(self, data):
        self._data = data

        self._curr_page = 0
        self._max_page = len(data)

    def _get_params(self):
        keyboard, row = [], []
        data = self._data[self._curr_page-1]
        keyboard.append([InlineKeyboardButton("Посмотреть в WIKI", url=data['link'])])

        if self._max_page > 1:
            if self._curr_page > 1:
                row.append(InlineKeyboardButton("⬅️", callback_data='prev',))

            if self._curr_page < self._max_page:
                row.append(InlineKeyboardButton("➡️", callback_data='next'))

        keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Вернуться назад", callback_data='back')])

        params = {'text': data['text'], 'reply_markup': InlineKeyboardMarkup(keyboard)}
        return params

    def next(self):
        self._curr_page += 1
        params = self._get_params()
        return params

    def prev(self):
        self._curr_page -= 1
        params = self._get_params()
        return params


class WIKI:
    _url = 'https://vatswiki.rt-dc.ru'
    _login = 'phenix'
    _password = None
    assert _password

    @classmethod
    def search(cls, text):
        try:
            wiki = dokuwiki.DokuWiki(url=cls._url, user=cls._login, password=cls._password, cookieAuth=True)
        except Exception as err:
            logger.error(err)
            return 500
        pattern = re.compile(r"\n{2,}")
        search_res = wiki.pages.search(text)
        vats_result = [res for res in search_res if res['id'].split(':')[0] == 'vats']

        if vats_result:
            data = []
            for result in vats_result:
                link = f"{cls._url}/doku.php?id={result['id']}"
                soup = bs4.BeautifulSoup(result['snippet'], 'lxml')
                formatted_text = pattern.sub("\n", soup.text)
                if result['title'] or formatted_text:
                    final_text = f"Заголовок: {result['title']}\n\nИскомое: {formatted_text[:4000]}"
                    data.append({'link': link, 'text': final_text})
            if data:
                return MessageKeyboardWIKI(data)
