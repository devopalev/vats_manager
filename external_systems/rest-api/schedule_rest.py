import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account


def _get_schedule(month_en):
    translator_month_ru = {'January': 'Январь', 'February': 'Февраль', 'March': 'Март', 'April': 'Апрель', 'May': 'Май',
                           'June': 'Июнь', 'July': 'Июль', 'August': 'Август', 'September': 'Сентябрь',
                           'October': 'Октябрь', 'November': 'Ноябрь', 'December': 'Декабрь'}

    month_ru = translator_month_ru.get(month_en)

    if month_ru == None:
        return None

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly'] # Области применения (
    # описание тут https://developers.google.com/identity/protocols/oauth2/scopes)

    # авторизация
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, '../credentials.json') # JSON файл из сервисного аккаунта
    credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)





    SAMPLE_SPREADSHEET_ID = '1BEQN1R-qZ7-co0OSczx5R3Bqwto4izpK5Vj5XbS06nE' # ID таблицы
    SAMPLE_RANGE_NAME = month_ru # диапазон ячеек для вывода (если весь лист, то только его название)


    service = build('sheets', 'v4', credentials=credentials).spreadsheets().values()
    result = service.get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                         range=SAMPLE_RANGE_NAME).execute()

    data_from_sheet = result.get('values', []) # вытягиваем данные из таблички

    return data_from_sheet

def check_holiday(date, users_data):
    schedule = _get_schedule(date.strftime('%B'))
    if schedule == None:
        return None

    result = {}
    index_day = schedule[2].index(date.strftime('%d').lstrip('0'))

    weekends = ['в', '!в', 'от', '!от', 'од', '!од', 'пк', 'б', '!б']


    for user in users_data:
        for row in schedule:
            # Пропускаем пустые строки
            if len(row) < 32:
                continue
            if user[3] == row[1]:
                if row[index_day].lower() in weekends:
                    state_today = False
                else:
                    text_schedule = row[index_day].split(" ")
                    schedule_start = date.replace(hour=int(text_schedule[0].split('.')[0]),
                                                 minute=int(text_schedule[0].split('.')[1]),
                                                 second=0, microsecond=0)
                    schedule_end = date.replace(hour=int(text_schedule[1].split('.')[0]),
                                                 minute=int(text_schedule[1].split('.')[1]),
                                                 second=0, microsecond=0)
                    state_today = [schedule_start, schedule_end]

                result.update({user[0]: state_today})
    # username_tg: False или список [datetime_start, datetime_end]
    return result

def check_duty(date, users_data):
    schedule = _get_schedule(date.strftime('%B'))
    DUTY_TIME = '10.00 19.00'

    result = []
    tomorrow_day = date.strftime('%d')
    index_day = schedule[2].index(tomorrow_day.lstrip('0'))

    for user in users_data:
        for row in schedule:
            # Пропускаем пустые строки
            if len(row) < 32:
                continue

            if user[3] == row[1]:
                if row[index_day] == DUTY_TIME:
                    result.append(user[0])
                break
    return result



