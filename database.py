import sqlite3
import os
import json
import telegram
import time
import threading
import datetime
from telegram.ext import *

PATH = os.path.dirname(__file__) + "/bot.db"


def sql_request(sql, data_python=()):
    connect = sqlite3.connect(PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connect.cursor()

    # data_python должен быть в формате (obj,) или[(obj1, obj2), (obj3, obj4)]
    if data_python:
        cursor.execute(sql, data_python)
    else:
        cursor.execute(sql)

    if sql[:6] in ('SELECT', 'PRAGMA'):
        result = cursor.fetchall()
        connect.close()
        return result
    elif sql[:6] in ('UPDATE', 'DELETE', 'INSERT', 'CREATE'):
        connect.commit()
        connect.close()
        return True


def get_users_access(access='user'):
    if access == 'root':
        sql = "SELECT username_tg FROM users WHERE access = 'root'"
    elif access == 'admin':
        sql = "SELECT username_tg FROM users WHERE access = 'admin' OR access = 'root'"
    elif access == 'user':
        sql = "SELECT username_tg FROM users"
    elif access == 'access_4':
        sql = "SELECT username_tg FROM users"
        users = [user[0] for user in sql_request(sql)]
        return [*users, *Settings.get_access_4()]
    elif access == 'access_5':
        sql = "SELECT username_tg FROM users"
        users = [user[0] for user in sql_request(sql)]
        return [*users, *Settings.get_access_4(), *Settings.get_access_5()]

    return [user[0] for user in sql_request(sql)]


def auth_user(access):
    """
    root - разработчики
    admin - гсп
    user - инженеры
    access_4 - ДС ОТТ
    access_5 - ОЭП
    """

    def decorator_auth(func_to_decorate):
        def new_func(*original_args, **original_kwargs):
            for arg in original_args:
                if type(arg) == telegram.update.Update:
                    if arg.effective_user.username in get_users_access(access):
                        return func_to_decorate(*original_args, **original_kwargs)
                    else:
                        return send_unauthorized_message(*original_args, **original_kwargs)

        return new_func

    return decorator_auth


def checking_privileges(user, access):
    if user in get_users_access(access):
        return True
    else:
        return False


def send_unauthorized_message(*original_args, msg_id=None):
    for arg in original_args:
        if isinstance(arg, telegram.update.Update):
            update = arg
            break
    else:
        raise AttributeError("Не найден update")

    for arg in original_args:
        if isinstance(arg, CallbackContext):
            context = arg
            break
    else:
        raise AttributeError("Не найден context")

    if not msg_id:
        if update.callback_query:
            context.bot.answer_callback_query(update.callback_query.id, text="Отказано в доступе!")
        else:
            answerMes = context.bot.send_message(chat_id=update.effective_chat.id, text="Отказано в доступе!")
            threading.Thread(target=send_unauthorized_message, args=(update, context),
                             kwargs={'msg_id': answerMes['message_id']}, daemon=True).start()
    else:
        time.sleep(5)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)


class Settings:
    # test - тестовая среда (без отправки уведомлений и т.д.)
    # prod - продуктивная среда
    _working_mode = None
    sql_request("CREATE TABLE if not exists settings (type text, value text, name text)")

    @classmethod
    def get_working_mode(cls):
        if cls._working_mode:
            return cls._working_mode
        else:
            sql = "SELECT value from settings WHERE type = 'working_mode'"
            cls._working_mode = sql_request(sql)[0][0]
            return cls._working_mode

    @classmethod
    def get_token(cls):
        if cls._working_mode == 'prod':
            sql = "SELECT value from settings WHERE type = 'token'"
        else:
            sql = "SELECT value from settings WHERE type = 'token_test'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_chat_id_events():
        sql = "SELECT value from settings WHERE type = 'chat_id_bug'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_chat_id_analyst():
        sql = f"SELECT value from settings WHERE type = 'chat_id_analystics'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_alarm_wait_inc():
        sql = "SELECT value from settings WHERE type = 'alarm_wait_inc'"
        return int(sql_request(sql)[0][0])

    @staticmethod
    def get_chat_id_duty():
        sql = "SELECT value from settings WHERE type = 'chat_id_duty'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_nttm_filter_direction():
        sql = "SELECT value from settings WHERE type = 'nttm_filter_direction'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_nttm_filter_vendor():
        sql = "SELECT value from settings WHERE type = 'nttm_filter_vendor'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_nttm_filter_queue():
        sql = "SELECT value from settings WHERE type = 'nttm_filter_queue'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_access_4():
        sql = "SELECT value from settings WHERE type = 'access_4'"
        return sql_request(sql)[0][0].split(';')

    @staticmethod
    def get_access_5():
        sql = "SELECT value from settings WHERE type = 'access_5'"
        return sql_request(sql)[0][0].split(';')

    @staticmethod
    def get_types_and_names():
        sql = "SELECT type, name from settings"
        return sql_request(sql)

    @staticmethod
    def get_setting(setting):
        sql = f"SELECT value from settings WHERE type = '{setting}'"
        return sql_request(sql)[0][0]

    @staticmethod
    def set_setting(setting, value):
        sql = f"UPDATE settings set value = '{value}' WHERE type = '{setting}'"
        sql_request(sql)

    @staticmethod
    def get_absence_minutes():
        sql = f"SELECT value FROM settings WHERE type = 'absence_minutes';"
        return int(sql_request(sql)[0][0])


class Data:
    sql_request("CREATE TABLE if not exists data (type text, value text)")

    @staticmethod
    def get_tickets_vendor(codec):
        sql = f"SELECT value from data WHERE type = 'tickets_vendor'"
        response = sql_request(sql)
        if len(response) > 0:
            data = json.loads(response[0][0])
            if len(data['tickets']) > 0:
                file_csv = f'Последнее обновление;{data["update_time"]}\r\n' \
                           f'ticket;incidents;description;description2\r\n'.encode(codec, errors='ignore')
                for ticket in data['tickets']:
                    file_csv += f"{ticket};{', '.join(data['tickets'][ticket]['inc'])};" \
                                f"{';'.join(data['tickets'][ticket]['description'])}\r\n".encode(codec, errors='ignore')
                return data["update_time"], file_csv
        return None, None

    @staticmethod
    def set_tickets_vendor(tickets_vendor):
        tickets_json = json.dumps(tickets_vendor, ensure_ascii=False)
        sql = f"UPDATE data set value = ? WHERE type = 'tickets_vendor'"
        sql_request(sql, (tickets_json,))

    @staticmethod
    def get_si_inc():
        sql = f"SELECT value from data WHERE type = 'si_tickets'"
        response = sql_request(sql)
        if response:
            return json.loads(response[0][0])
        else:
            return response

    @classmethod
    def add_si_inc(cls, inc_si: str):
        curr = cls.get_si_inc()
        new = [inc_si]
        if curr:
            new.extend(curr)
        print(json.dumps(new))
        sql = f"UPDATE data set value = '{json.dumps(new)}' WHERE type = 'si_tickets'"
        sql_request(sql)

    @classmethod
    def del_si_inc(cls, inc_si: str):
        curr = cls.get_si_inc()
        if curr:
            curr.remove(int(inc_si))
        sql = f"UPDATE data set value = '{json.dumps(curr)}' WHERE type = 'si_tickets'"
        sql_request(sql)


class Users:
    sql_request("""CREATE TABLE if not exists users (username_tg text, access text, username_vats text, 
    full_name text, username_skuf text, chat_id text, analytics BOOLEAN)""")

    @staticmethod
    def get_user_chat_id(username_tg):
        sql = f"SELECT chat_id FROM users WHERE username_tg = '{username_tg}'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_custom_params(*args):
        params = ', '.join(args)
        sql = f"SELECT {params} FROM users;"
        return sql_request(sql)

    @staticmethod
    def get_users_info():
        sql = "SELECT * FROM users"
        return sql_request(sql)

    @staticmethod
    def get_fullname_by_username_tg(username_tg):
        sql = f"SELECT full_name FROM users WHERE username_tg = '{username_tg}'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_username_skuf(username_tg):
        sql = f"SELECT username_skuf FROM users WHERE username_tg = '{username_tg}'"
        return sql_request(sql)[0][0]

    @staticmethod
    def get_users_column_name():
        sql = "PRAGMA TABLE_INFO(users);"
        result = []
        for column in sql_request(sql):
            result.append(column[1])
        return result

    @staticmethod
    def get_user_username_vats(username_tg):
        sql = f"SELECT username_vats FROM users WHERE username_tg = '{username_tg}'"
        return sql_request(sql)[0]

    @staticmethod
    def change_analytics(username_tg):
        sql = f"SELECT analytics FROM users WHERE username_tg = '{username_tg}'"
        curr_value = sql_request(sql)[0][0]
        if curr_value:
            new_value = 0
        else:
            new_value = 1
        sql = f"UPDATE users set analytics = {new_value} WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def set_user_username_tg(old_username_tg, new_username_tg):
        sql = f"UPDATE users set username_tg = '{new_username_tg}' WHERE username_tg = '{old_username_tg}'"
        sql_request(sql)

    @staticmethod
    def set_user_access(username_tg, access):
        sql = f"UPDATE users set access = '{access}' WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def set_user_username_vats(username_tg, username_vats):
        if username_vats == 'None':
            data_python = (None,)
            sql = f"UPDATE users set username_vats = ? WHERE username_tg = '{username_tg}'"
            sql_request(sql, data_python)
        else:
            sql = f"UPDATE users set username_vats = '{username_vats}' WHERE username_tg = '{username_tg}'"
            sql_request(sql)

    @staticmethod
    def set_user_full_name(username_tg, full_name):
        sql = f"UPDATE users set full_name = '{full_name}' WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def set_user_username_skuf(username_tg, username_skuf):
        sql = f"UPDATE users set username_skuf = '{username_skuf}' WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def del_user(username_tg):
        sql = f"DELETE from users WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def check_chat_id(username_tg):
        sql = f"SELECT chat_id FROM users WHERE username_tg = '{username_tg}'"
        result = sql_request(sql)
        if result[0][0] == None or result[0][0] == 'None':
            return False
        else:
            return True

    @staticmethod
    def set_user_chat_id(username_tg, chat_id):
        sql = f"UPDATE users set chat_id = '{chat_id}' WHERE username_tg = '{username_tg}'"
        sql_request(sql)

    @staticmethod
    def create_user_tg(username_tg):
        sql = f"INSERT INTO users(username_tg) VALUES ('{username_tg}')"
        sql_request(sql)

    @staticmethod
    def del_user_chat_id(username_tg):
        data_python = (None,)
        sql = f"UPDATE users set chat_id = ? WHERE username_tg = '{username_tg}'"
        sql_request(sql, data_python)


class Calls:
    sql_request("""CREATE TABLE if not exists calls (type text, state text, session_id text, start_time text, 
    end_time text, from_number text, request_number text)""")

    @staticmethod
    def get_calls_bd():
        connect = sqlite3.connect(os.path.dirname(__file__) + "/bot.db")
        cursor = connect.cursor()

        cursor.execute("SELECT * FROM calls ORDER BY start_time DESC")
        while True:
            call = cursor.fetchone()
            if call:
                yield call
            else:
                break
        connect.close()

    @staticmethod
    def fix_calls():
        # Обновление вызовов принудительно
        sql = f"""UPDATE calls SET end_time = '{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}', 
                        state = 'disconnected' WHERE state = 'connected';"""
        sql_request(sql)