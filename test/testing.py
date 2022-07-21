from schedule_job import schedule
import datetime
import calendar
import unittest
import warnings


class MyTestCase(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings(action="ignore", category=ResourceWarning)

    def test_schedule(self):
        date = datetime.datetime.now().replace(day=1)
        days_in_month = calendar.monthrange(date.year, date.month)[1]

        with self.subTest():
            # Проверка по каждому дню месяца
            for _ in range(days_in_month):
                res = schedule.get_work_time_user(date, 'Опалев Максим Сергеевич')
                if isinstance(res, list):
                    self.assertEqual(type(res[0]), type(date))
                else:
                    self.assertIsInstance(res, bool)
                self.assertIsInstance(schedule.check_work_time_user(date, 'Опалев Максим Сергеевич'), bool)
                date += datetime.timedelta(days=1)

        with self.subTest():
            res = schedule.get_schedule_today().items()
            for full_name, date_list in res:
                self.assertIsInstance(full_name, str)
                if date_list:
                    for date_ in date_list:
                        self.assertEqual(type(date_), type(date))
                else:
                    self.assertIsInstance(date_list, bool)
        with self.subTest():
            self.assertIsInstance(schedule.get_duty_today(), list)
        with self.subTest():
            self.assertIsInstance(schedule.get_duty_tomorrow(), list)


if __name__ == '__main__':
    unittest.main()

