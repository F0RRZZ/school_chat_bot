import csv
import datetime as dt
import os
import sqlite3
import requests
import telebot
import schedule
import data
import keep_alive

from time import sleep
from bs4 import BeautifulSoup
from telebot import types
from threading import Thread
from telebot.apihelper import ApiTelegramException


token = os.environ["TOKEN"]
bot = telebot.TeleBot(token, parse_mode=None)
URL = "https://al-school.ru/category/новости/"


def is_user_admin(telegram_id):
    with sqlite3.connect("school_db.sqlite") as con:
        cur = con.cursor()
        for i in cur.execute("""SELECT telegram_id FROM admins""").fetchall():
            if str(telegram_id) == i[0]:
                return True
        return False


def is_user_in_database(telegram_id):
    with sqlite3.connect("school_db.sqlite") as con:
        cur = con.cursor()
        for i in cur.execute("""SELECT student_id FROM students""").fetchall():
            if str(telegram_id) == i[0]:
                return True
        return False


def mailing_checker():
    while True:
        schedule.run_pending()
        sleep(1)


def mail_next_lessons():
    if dt.datetime.now().strftime("%A") in ("Saturday", "Sunday"):
        return
    with sqlite3.connect('school_db.sqlite') as db:
        cur = db.cursor()
        for i in cur.execute("""SELECT student_id, class, mailing FROM students""").fetchall():
            if str(i[-1]) == '1':
                with open(file=f'schedules/{i[1]}.csv', mode='r', encoding='utf-8') as csvfile:
                    time = ['05:20', '06:05', '06:55', '07:45', '08:45', '09:35', '10:20']
                    days = {"Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда", "Thursday": "Четверг",
                            "Friday": "Пятница"}
                    lesson_num = time.index(dt.datetime.now().strftime('%H:%M'))
                    day = days[dt.datetime.now().strftime("%A")]
                    reader = csv.DictReader(csvfile, delimiter=',')
                    lesson = list(reader)[lesson_num][day]
                    try:
                        bot.send_message(i[0], f'Ваш следующий урок: {lesson}')
                    except ApiTelegramException as e:
                        if e.description == "Forbidden: bot was blocked by the user":
                            print(
                                "Attention please! The user {} has blocked the bot. I can't send anything to them".format(
                                    i[0]))


def function_to_run():
    return mail_next_lessons()


def start_buttons(message):
    """Main buttons"""
    admin = is_user_admin(message.chat.id)
    if admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        table = types.KeyboardButton("Расписания📋")
        service = types.KeyboardButton("Персонал🧑‍🏫")
        cabinets = types.KeyboardButton("Кабинеты🚪")
        additional_lessons = types.KeyboardButton("Дополнительные занятия🗒")
        news = types.KeyboardButton("Новости📰")
        mailing = types.KeyboardButton("Вкл/откл рассылку уроков📩")
        problem = types.KeyboardButton("Сообщить о проблеме❗")
        if not is_user_in_database(message.chat.id):
            markup.add(table, service, cabinets, additional_lessons, news, problem)
        else:
            markup.add(table, service, cabinets, additional_lessons, news, mailing, problem)
        bot.send_message(message.chat.id, 'Выберите интересующую вас тему:', reply_markup=markup)
    else:
        user_in_database = is_user_in_database(message.chat.id)
        if user_in_database:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            table = types.KeyboardButton("Расписания📋")
            service = types.KeyboardButton("Персонал🧑‍🏫")
            cabinets = types.KeyboardButton("Кабинеты🚪")
            additional_lessons = types.KeyboardButton("Дополнительные занятия🗒")
            news = types.KeyboardButton("Новости📰")
            mailing = types.KeyboardButton("Вкл/откл рассылку уроков📩")
            problem = types.KeyboardButton("Сообщить о проблеме❗")
            db_delete = types.KeyboardButton("Удалить себя из базы данных🚫")
            markup.add(table, service, cabinets, additional_lessons, news, mailing, problem, db_delete)
            bot.send_message(message.chat.id, 'Выберите интересующую вас тему:', reply_markup=markup)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(*list(types.KeyboardButton(f"{i}") for i in range(5, 12)))
            bot.send_message(message.chat.id, 'Вас нет в базе данных\nВыберите класс: ', reply_markup=markup)


@bot.message_handler(commands=['start'])
def start_message(message):
    markup_site = types.InlineKeyboardMarkup()
    markup_site.add(types.InlineKeyboardButton("Наш сайт", url=URL))
    bot.send_photo(message.chat.id, open('school_photo.png', 'rb'))
    bot.send_message(message.chat.id, "Вас приветствует бот школы №11 г.Нальчика."
                                      " Я отвечу на все ваши вопросы 😉", reply_markup=markup_site)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, 'Вы вошли с админ-аккаунта\n'
                                          'Вам доступны дополнительные команды и функции:\n'
                                          '/alert - Отправить экстренное сообщение\n'
                                          'Чтобы сменить расписание, вы можете отправить CSV-файл с расписанием, указав в описании класс\n'
                                          'CSV-файл можно сгенерировать в программе School Schedule')

    start_buttons(message)


@bot.message_handler(commands=['alert'])
def send_alert(message):
    if is_user_admin(message.chat.id):
        if message.text == '/alert':
            bot.send_message(message.chat.id,
                             'Инструцкия по использованию команды:\n'
                             '/alert <КЛАСС/ВСЕ> <СООБЩЕНИЕ>\n'
                             'Например:\n'
                             '/alert 11А Сообщение (отправка сообщения 11А классу)\n'
                             'ИЛИ\n'
                             '/alert ВСЕ Сообщение (отправка сообщения всем ученикам)')
        else:
            text = message.text.split()
            with sqlite3.connect('school_db.sqlite') as db:
                cur = db.cursor()
                if text[1].lower() == 'все':
                    for i in cur.execute("""SELECT student_id FROM students""").fetchall():
                        try:
                            bot.send_message(i[0], ' '.join(text[2:]))
                        except ApiTelegramException as e:
                            if e.description == "Forbidden: bot was blocked by the user":
                                print(
                                    "Attention please! The user {} has blocked the bot. I can't send anything to them".format(
                                        message.chat.id))
                else:
                    for i in cur.execute("""SELECT student_id FROM students
                                            WHERE class = ?""", (text[1].upper(),)).fetchall():
                        try:
                            bot.send_message(i[0], ' '.join(text[2:]))
                        except ApiTelegramException as e:
                            if e.description == "Forbidden: bot was blocked by the user":
                                print(
                                    "Attention please! The user {} has blocked the bot. I can't send anything to them".format(
                                        message.chat.id))
            if text[1].upper() in ['5А', '5Б', '5В.csv', '5Г', '5Д', '6А', '6Б', '6В', '6Г', '7А', '7Б',
                                   '7В', '7Г', '8А', '8Б', '8В', '8Г',
                                   '9А', '9Б', '9В', '9Г', '10А', '11А', 'ВСЕ']:
                bot.send_message(message.chat.id, f'Сообщение успешно доставлено {text[1]}')
            else:
                bot.send_message(message.chat.id, 'Введены неверные данные')
    else:
        bot.send_message(message.chat.id, 'Вы не можете воспользоваться этой функцией')


@bot.message_handler(content_types=['document'])
def change_schedule(message):
    if is_user_admin(message.chat.id):
        file_info = bot.get_file(message.document.file_id)
        class_name = message.caption
        try:
            if class_name in ['5А', '5Б', '5В', '5Г', '5Д', '6А', '6Б', '6В', '6Г', '7А', '7Б', '7В', '7Г', '8А', '8Б',
                              '8В', '8Г', '9А', '9Б', '9В', '9Г', '10А', '11А']:
                downloaded_file = bot.download_file(file_info.file_path)
                src = os.getcwd() + "\\" + message.document.file_name
                with open(src, mode='wb') as file:
                    file.write(downloaded_file)

                with open(src, encoding='utf-8') as file:
                    reader = csv.DictReader(file, delimiter=',')
                    schedule = []
                    for i in reader:
                        schedule.append(i)
                    f = open(f"schedules/{class_name}.csv", "w")
                    f.truncate()
                    f.close()
                    with open(f"schedules/{class_name}.csv", encoding='utf-8', mode='w') as file2:
                        writer = csv.DictWriter(file2, fieldnames=list(schedule[0].keys()), delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
                        writer.writeheader()
                        for i in schedule:
                            writer.writerow(i)
                bot.send_message(message.chat.id, f'Расписание для {class_name} успешно изменено!')
                os.remove(src)
            else:
                bot.send_message(message.chat.id, 'Не существует такого класса.')
        except Exception:
            bot.send_message(message.chat.id, 'Произошла ошибка.')


@bot.message_handler(content_types='text')
def reply_message(message):
    if is_user_in_database(message.chat.id) or is_user_admin(message.chat.id):
        if message.text == 'Персонал🧑‍🏫':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            teachers = types.KeyboardButton("Учителя🧑‍🏫")
            administraition = types.KeyboardButton("Администрация🏤")
            service = types.KeyboardButton("Обслуживающий персонал🧍")
            markup.add(teachers, administraition, service)
            bot.send_message(message.chat.id, 'Выберите интересующий вариант: ', reply_markup=markup)

        elif message.text in ["Учителя🧑‍🏫", "Администрация🏤", "Обслуживающий персонал🧍"]:
            result_message = []
            info = {"Учителя🧑‍🏫": data.TEACHERS, "Администрация🏤": data.ADMINISTRATION,
                    "Обслуживающий персонал🧍": data.SERVICE}
            for num, (name, post) in enumerate(info[message.text].items()):
                result_message.append(f'{num + 1}. {name} \n {post}')
                result_message.append(' ')
            bot.send_message(message.chat.id, '\n'.join(result_message))
            start_buttons(message)

        elif message.text == "Расписания📋":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            rings = types.KeyboardButton("Расписание звонков🔔")
            lessons = types.KeyboardButton("Расписание уроков📚")
            markup.add(rings, lessons)
            bot.send_message(message.chat.id, 'Выберите интересующий вариант: ', reply_markup=markup)

        elif message.text == "Расписание звонков🔔":
            bot.send_message(message.chat.id, data.RINGS)
            start_buttons(message)

        elif message.text == "Расписание уроков📚":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(*list(types.KeyboardButton(f"{i}") for i in range(5, 12)))
            bot.send_message(message.chat.id, 'Выберите класс: ', reply_markup=markup)

        elif message.text in ['5', '6', '7', '8', '9', '10', '11']:
            letters = {'5': 'АБВГД', '6': 'АБВГ', '7': 'АБВГ', '8': 'АБВГ', '9': 'АБВГ', '10': 'А', '11': 'А'}
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(*list(types.KeyboardButton(f"{message.text}{i}") for i in letters[message.text]))
            bot.send_message(message.chat.id, 'Выберите класс: ', reply_markup=markup)

        elif message.text in ['5А', '5Б', '5В', '5Г', '5Д', '6А', '6Б', '6В', '6Г', '7А', '7Б', '7В', '7Г', '8А', '8Б',
                              '8В', '8Г', '9А', '9Б', '9В', '9Г', '10А', '11А']:
            days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']
            result_message = ''
            with open(f'schedules/{message.text}.csv', encoding='utf-8', mode='r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',')
                subjects = list(reader)
                for i in range(5):
                    result_message += days[i] + ':' + '\n'
                    for index, j in enumerate(subjects):
                        result_message += str(index + 1) + '. ' + j[days[i]] + '\n'
                    result_message += '\n'
            bot.send_message(message.chat.id, result_message)
            start_buttons(message)

        elif message.text == "Кабинеты🚪":
            bot.send_message(message.chat.id, '\n'.join(data.CABINETS))

        elif message.text == "Дополнительные занятия🗒":
            result = []
            for num, lesson in enumerate(data.ADDITIONAL):
                result.append(f"{num + 1}. {lesson}")
            bot.send_message(message.chat.id, '\n'.join(result))

        elif message.text == "Новости📰":
            bot.send_message(message.chat.id, "Последние новости: ")
            soup = BeautifulSoup(requests.get(URL).text, "html.parser")
            themes = [i.getText() for i in soup.find('div', {'class': 'span-14'}).find_all('h2')][1:4]
            text = [i.getText() for i in soup.find('div', {'class': 'span-14'}).find_all('p')][:3]
            links = [i.get('href') for i in soup.find('div', {'class': 'span-14'}).find_all('a')][::4]
            for i in range(3):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Ссылка на продолжение новости", url=links[i]))
                bot.send_message(message.chat.id, '\n'.join([f'*{themes[i]}*', '', text[i]]), reply_markup=markup,
                                 parse_mode="Markdown")

        elif message.text == "Сообщить о проблеме❗":
            bot.send_message(message.chat.id,
                             "Вы можете обратиться с проблемой на почту school11bot.problem@gmail.com\n"
                             "Мы обязательно рассмотрим ваше обращение😉")

        elif message.text == 'Удалить себя из базы данных🚫':
            with sqlite3.connect('school_db.sqlite') as db:
                cur = db.cursor()
                cur.execute("""DELETE from students WHERE student_id = ?""", (message.chat.id,))
                db.commit()
            bot.send_message(message.chat.id, 'Вы удалены из базы данных')
            start_buttons(message)
        elif message.text == "Вкл/откл рассылку уроков📩":
            if is_user_in_database(message.chat.id):
                with sqlite3.connect('school_db.sqlite') as db:
                    cur = db.cursor()
                    mailing = cur.execute("""SELECT mailing FROM students WHERE student_id = ?""", (message.chat.id, )).fetchall()[0][0]
                    if mailing == 0:
                        bot.send_message(message.chat.id, "Вы включили рассылку уроков.\nТеперь в конце каждого урока я буду писать вам, какой урок следующий😉")
                    else:
                        bot.send_message(message.chat.id, "Вы отключили рассылку уроков.")
                    cur.execute("""UPDATE students SET mailing = ? WHERE student_id = ?""", ((mailing + 1) % 2, message.chat.id,))
        else:
            bot.send_message(message.chat.id, 'Я вас не понимаю ☹')
    else:
        if message.text in ['5А', '5Б', '5В.csv', '5Г', '5Д', '6А', '6Б', '6В', '6Г', '7А', '7Б', '7В', '7Г', '8А',
                            '8Б',
                            '8В', '8Г',
                            '9А', '9Б', '9В', '9Г', '10А', '11А']:
            with sqlite3.connect('school_db.sqlite') as db:
                cur = db.cursor()
                cur.execute("""INSERT INTO students(student_id, class) VALUES (?, ?)""",
                            (message.chat.id, message.text,))
                db.commit()
            start_buttons(message)
        elif message.text in ['5', '6', '7', '8', '9', '10', '11']:
            letters = {'5': 'АБВГД', '6': 'АБВГ', '7': 'АБВГ', '8': 'АБВГ', '9': 'АБВГ', '10': 'А', '11': 'А'}
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(*list(types.KeyboardButton(f"{message.text}{i}") for i in letters[message.text]))
            bot.send_message(message.chat.id, 'Выберите класс: ', reply_markup=markup)


if __name__ == "__main__":
    # Время сдвинуто на 3 часа назад, потому что код заупскается в Великобритании
    schedule.every().day.at("05:20").do(function_to_run)
    schedule.every().day.at("06:05").do(function_to_run)
    schedule.every().day.at("06:55").do(function_to_run)
    schedule.every().day.at("07:45").do(function_to_run)
    schedule.every().day.at("08:45").do(function_to_run)
    schedule.every().day.at("09:35").do(function_to_run)
    schedule.every().day.at("10:20").do(function_to_run)

    Thread(target=mailing_checker).start()

    keep_alive.keep_alive()
    bot.infinity_polling()
