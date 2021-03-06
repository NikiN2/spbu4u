# -*- coding: utf-8 -*-
import telebot
import requests
import sqlite3
import logging
import json
import time
from datetime import datetime, timedelta, time as dt_time
import flask
from flask_sslify import SSLify
import registration_functions as reg_func
import functions as func
from yandex_timetable import get_yandex_timetable_data
from sql_updater import schedule_update
from constants import release_token, emoji, briefly_info_answer, my_id, \
    full_info_answer, webhook_url_base, webhook_url_path, week_day_number, \
    all_stations, all_stations_const, week_day_titles, subject_short_type_revert


bot = telebot.TeleBot(release_token, threaded=False)
app = flask.Flask(__name__)
sslify = SSLify(app)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

main_keyboard = telebot.types.ReplyKeyboardMarkup(True)
if time.localtime().tm_mon in [12, 1, 5, 6]:
    main_keyboard.row("СЕССИЯ", "Расписание")
else:
    main_keyboard.row("Расписание")
main_keyboard.row(emoji["info"], emoji["star"], emoji["settings"],
                  emoji["suburban"], emoji["editor"])

server_timedelta = timedelta(hours=3)


@bot.message_handler(commands=["start"])
@bot.message_handler(func=lambda mess: mess.text == "Сменить группу",
                     content_types=["text"])
def start_handler(message):
    answer = ""
    if message.text == "/start":
        answer = "Приветствую!\n"
    answer += "Загружаю список направлений..."
    bot_msg = bot.send_message(message.chat.id, answer)
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Укажи свое направление:"
    url = "https://timetable.spbu.ru/api/v1/study/divisions"
    divisions = requests.get(url).json()
    division_names = [division["Name"] for division in divisions]
    divisions_keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    for division_name in division_names:
        divisions_keyboard.row(division_name)
    divisions_keyboard.row("Проблема", "Завершить")
    data = json.dumps(divisions)

    sql_con = sqlite3.connect("Bot_db")
    cursor = sql_con.cursor()
    cursor.execute("""DELETE FROM user_choice WHERE user_id = ?""",
                   (message.chat.id, ))
    sql_con.commit()
    cursor.execute("""INSERT INTO user_choice (user_id, divisions_json)
                      VALUES (?, ?)""", (message.chat.id, data))
    sql_con.commit()
    cursor.close()
    sql_con.close()
    bot.edit_message_text(text="Готово!", chat_id=message.chat.id,
                          message_id=bot_msg.message_id)
    bot.send_message(message.chat.id, answer, reply_markup=divisions_keyboard)
    reg_func.set_next_step(message.chat.id, "select_division")


@bot.message_handler(func=lambda mess: mess.text == "Проблема",
                     content_types=["text"])
def problem_text_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Если возникла проблема, то:\n" \
             "1. возможно, информация по этому поводу есть в нашем канале" \
             " - @Spbu4u_news;\n" \
             "2. ты всегда можешь связаться с " \
             "<a href='https://t.me/eeonedown'>разработчиком</a>."
    bot.send_message(message.chat.id, answer,
                     disable_web_page_preview=True,
                     parse_mode="HTML")


@bot.message_handler(commands=["exit"])
@bot.message_handler(func=lambda mess: mess.text == "Завершить",
                     content_types=["text"])
def exit_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    func.delete_user(message.chat.id, only_choice=False)
    remove_keyboard = telebot.types.ReplyKeyboardRemove(True)
    answer = "До встречи!"
    bot.send_message(message.chat.id, answer, reply_markup=remove_keyboard)


@bot.message_handler(func=lambda mess:
                     reg_func.get_step(mess.chat.id) == "select_division" and
                     mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def select_division_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.select_division(message)
    return


@bot.message_handler(func=lambda mess:
                     reg_func.get_step(mess.chat.id) == "select_study_level" and
                     mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def select_study_level_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.select_study_level(message)
    return


@bot.message_handler(func=lambda mess: reg_func.get_step(
    mess.chat.id) == "select_study_program_combination" and
                     mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def select_study_program_combination_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.select_study_program_combination(message)
    return


@bot.message_handler(func=lambda mess:
                     reg_func.get_step(mess.chat.id) == "select_admission_year"
                     and mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def select_admission_year_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.select_admission_year(message)
    return


@bot.message_handler(func=lambda mess:
                     reg_func.get_step(mess.chat.id) == "select_student_group"
                     and mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def select_student_group_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.select_student_group(message)
    return


@bot.message_handler(func=lambda mess:
                     reg_func.get_step(mess.chat.id) == "confirm_choice" and
                     mess.text != "/home" and mess.text != "Назад",
                     content_types=["text"])
def confirm_choice_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    reg_func.confirm_choice(message)
    return


@bot.message_handler(func=lambda mess: not func.is_user_exist(mess.chat.id),
                     content_types=["text"])
def not_exist_user_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Чтобы начать пользоваться сервисом, необходимо " \
             "зарегистрироваться.\nВоспользуйся коммандой /start"
    bot.send_message(message.chat.id, answer)


@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda mess: mess.text == emoji["info"],
                     content_types=["text"])
def help_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    inline_full_info_keyboard = telebot.types.InlineKeyboardMarkup()
    ''' delete this?
    inline_full_info_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Полное ИНФО"]])
    '''
    answer = briefly_info_answer
    bot.send_message(message.chat.id, answer,
                     parse_mode="HTML",
                     reply_markup=inline_full_info_keyboard,
                     disable_web_page_preview=True)


@bot.message_handler(commands=["home"])
@bot.message_handler(func=lambda mess: mess.text == "Назад" or
                     mess.text == emoji["back"], content_types=["text"])
def home_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    func.delete_user(message.chat.id, only_choice=True)
    answer = "Главное меню"
    bot.send_message(message.chat.id, answer, reply_markup=main_keyboard)


@bot.message_handler(commands=["settings"])
@bot.message_handler(func=lambda mess: mess.text == emoji["settings"],
                     content_types=["text"])
def settings_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    func.delete_user(message.chat.id, only_choice=True)
    settings_keyboard = telebot.types.ReplyKeyboardMarkup(True)
    settings_keyboard.row("Сменить группу", "Завершить")
    settings_keyboard.row("Назад", "Проблема")
    answer = "Настройки"
    bot.send_message(message.chat.id, answer, reply_markup=settings_keyboard)


@bot.message_handler(func=lambda mess: mess.text == "Расписание",
                     content_types=["text"])
def schedule_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Меню расписания"
    schedule_keyboard = telebot.types.ReplyKeyboardMarkup(True)
    schedule_keyboard.row("Сегодня", "Завтра", "Неделя")
    schedule_keyboard.row(emoji["back"], emoji["bust_in_silhouette"],
                          emoji["arrows_counterclockwise"],
                          emoji["alarm_clock"])
    bot.send_message(message.chat.id, answer, reply_markup=schedule_keyboard)


@bot.message_handler(func=lambda mess: mess.text == "Сегодня")
def today_schedule_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    today_moscow_datetime = datetime.today() + server_timedelta
    today_moscow_date = today_moscow_datetime.date()
    json_day = func.get_json_day_data(message.chat.id, today_moscow_date)
    full_place = func.is_full_place(message.chat.id)
    answer = func.create_schedule_answer(json_day, full_place, message.chat.id)
    func.send_long_message(bot, answer, message.chat.id)


@bot.message_handler(func=lambda mess: mess.text == "Завтра")
def tomorrow_schedule_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    tomorrow_moscow_datetime = datetime.today() + server_timedelta + \
        timedelta(days=1)
    tomorrow_moscow_date = tomorrow_moscow_datetime.date()
    json_day = func.get_json_day_data(message.chat.id, tomorrow_moscow_date)
    full_place = func.is_full_place(message.chat.id)
    answer = func.create_schedule_answer(json_day, full_place, message.chat.id)
    func.send_long_message(bot, answer, message.chat.id)


@bot.message_handler(func=lambda mess: mess.text == "Неделя")
def calendar_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Выбери день:"
    week_day_calendar = telebot.types.InlineKeyboardMarkup()
    week_day_calendar.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in week_day_number.keys()])
    week_day_calendar.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Вся неделя"]])
    bot.send_message(message.chat.id, answer, reply_markup=week_day_calendar)


@bot.message_handler(func=lambda mess: mess.text == emoji["alarm_clock"])
def sending_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Здесь ты можешь <b>подписаться</b> на рассылку расписания на " + \
             "следующий день или <b>отписаться</b> от неё.\n" + \
             "Рассылка производится в 21:00"
    sending_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if func.is_sending_on(message.chat.id):
        sending_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name,
                                                 callback_data="Отписаться")
              for name in [emoji["cross_mark"] + " Отписаться"]])
    else:
        sending_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name,
                                                 callback_data="Подписаться")
              for name in [emoji["check_mark"] + " Подписаться"]])
    bot.send_message(message.chat.id, answer, parse_mode="HTML",
                     reply_markup=sending_keyboard)


@bot.message_handler(func=lambda mess: mess.text == emoji["star"])
def rate_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Оцените качество сервиса:"
    user_rate = func.get_user_rate(message.chat.id)
    rate_keyboard = telebot.types.InlineKeyboardMarkup(row_width=5)
    rate_keyboard.add(*[telebot.types.InlineKeyboardButton(
        text=emoji["star2"] if user_rate < count_of_stars else emoji["star"],
        callback_data=str(count_of_stars))
        for count_of_stars in (1, 2, 3, 4, 5)])
    rate_keyboard.add(
        *[telebot.types.InlineKeyboardButton(text=name,
                                             callback_data=name)
          for name in ["Связь", "Статистика"]])
    bot.send_message(message.chat.id, answer, parse_mode="HTML",
                     reply_markup=rate_keyboard)


@bot.message_handler(func=lambda mess: mess.text == emoji["suburban"])
def suburban_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    suburban_keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    suburban_keyboard.row("Домой", "В Универ", "Маршрут")
    suburban_keyboard.row("Назад", "Персонализация")
    answer = "Меню расписания электричек\n\n" \
             "Данные предоставлены сервисом " \
             "<a href = 'http://rasp.yandex.ru/'>Яндекс.Расписания</a>"
    bot.send_message(message.chat.id,
                     answer,
                     reply_markup=suburban_keyboard,
                     parse_mode='HTML',
                     disable_web_page_preview=True)


@bot.message_handler(func=lambda mess: mess.text == "В Универ")
def to_university_handler(message):
    bot.send_chat_action(message.chat.id, "typing")

    from_station = func.get_fom_station_code(message.chat.id)
    if func.is_univer(message.chat.id):
        to_station = all_stations["Университетская (Университет)"]
    else:
        to_station = all_stations["Старый Петергоф"]

    server_datetime = datetime.today() + server_timedelta
    data = get_yandex_timetable_data(from_station, to_station, server_datetime)
    answer = data["answer"]
    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if data["is_tomorrow"]:
        bot.send_message(message.chat.id, emoji["warning"] +
                         " На сегодня нет электричек")
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Оставшиеся", "Обновить"]])
    bot.send_message(message.chat.id,
                     answer,
                     reply_markup=update_keyboard,
                     parse_mode='HTML',
                     disable_web_page_preview=True)


@bot.message_handler(func=lambda mess: mess.text == "Домой")
def from_university_handler(message):
    bot.send_chat_action(message.chat.id, "typing")

    to_station = func.get_fom_station_code(message.chat.id)
    if func.is_univer(message.chat.id):
        from_station = all_stations["Университетская (Университет)"]
    else:
        from_station = all_stations["Старый Петергоф"]

    server_datetime = datetime.today() + server_timedelta
    data = get_yandex_timetable_data(from_station, to_station, server_datetime)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if data["is_tomorrow"]:
        bot.send_message(message.chat.id, emoji["warning"] +
                         " На сегодня нет электричек")
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Оставшиеся", "Обновить"]])
    bot.send_message(message.chat.id,
                     answer,
                     reply_markup=update_keyboard,
                     parse_mode='HTML',
                     disable_web_page_preview=True)


@bot.message_handler(func=lambda mess: mess.text == "Маршрут")
def own_trail_handler(message):
    answer = "Выбери начальную станцию:"
    start_station_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for station_title in all_stations_const:
        start_station_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in [station_title]])
    bot.send_message(message.chat.id, answer,
                     reply_markup=start_station_keyboard)


@bot.message_handler(func=lambda mess: mess.text == "Персонализация")
def personalisation_handler(message):
    answer = "Здесь ты можешь настроить <b>домашнюю</b> и " \
             "<b>Университетскую</b> станции для команд <i>Домой</i> и " \
             "<i>В Универ</i>"
    inline_keyboard = telebot.types.InlineKeyboardMarkup(True)
    inline_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Домашняя"]])
    inline_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Университетская"]])
    bot.send_message(message.chat.id, answer,
                     reply_markup=inline_keyboard, parse_mode="HTML")


@bot.message_handler(func=lambda mess: mess.text == emoji["editor"])
def schedule_editor_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Редактор расписания"
    schedule_editor_keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    schedule_editor_keyboard.row("Скрыть занятие")
    schedule_editor_keyboard.row("Назад", "Адрес", "Вернуть")
    bot.send_message(message.chat.id,
                     answer,
                     reply_markup=schedule_editor_keyboard,
                     parse_mode='HTML')


@bot.message_handler(func=lambda mess: mess.text == "Адрес",
                     content_types=["text"])
def place_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "В каком формате отображать адрес занятий?\nСейчас: "
    place_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if func.is_full_place(message.chat.id):
        answer += "<b>Полностью</b>"
        place_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name,
                                                 callback_data="Аудитория")
              for name in ["Только аудитория"]])
    else:
        answer += "<b>Только аудитория</b>"
        place_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name,
                                                 callback_data="Полностью")
              for name in ["Полностью"]])
    bot.send_message(message.chat.id, answer, parse_mode="HTML",
                     reply_markup=place_keyboard)


@bot.message_handler(func=lambda mess: mess.text == "Скрыть занятие")
def hide_lesson_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Выбери день, когда есть это занятие:"
    json_week_data = func.get_json_week_data(my_id)
    days = json_week_data["Days"]
    days_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for day in days:
        days_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
              for name in [day["DayString"].split(", ")[0].capitalize()]])
    days_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Отмена"]])
    bot.send_message(message.chat.id, answer, reply_markup=days_keyboard)


@bot.message_handler(func=lambda mess: mess.text == "Вернуть")
def return_hided_lesson(message):
    data = func.get_hide_lessons_data(message.chat.id)
    ids_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if len(data):
        answer = "Вот список скрытых тобой занятий:\n\n"
        for lesson in data:
            answer += "<b>id: {0}</b>\n<b>Название</b>: {1}\n<b>Тип</b>: {2}" \
                      "\n<b>День</b>: {3}\n<b>Время</b>: {4}\n\n".format(
                          lesson[0], lesson[1], lesson[2], lesson[3], lesson[4])
            ids_keyboard.row(
                *[telebot.types.InlineKeyboardButton(text=name,
                                                     callback_data=name)
                  for name in ["{0} - {1}".format(lesson[0], lesson[1])[:32]]]
            )
        ids_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
              for name in ["Отмена", "Вернуть всё"]]
        )
        answer += "Выбери то, которое хочешь вернуть:"
    else:
        answer = "Скрытых занятий нет"
    if len(answer) >= 3000:
        answers = answer.split("\n\n")
        for answer in answers[:-1]:
            bot.send_message(message.chat.id, answer, parse_mode="HTML")
        answer = answers[-1]
    bot.send_message(message.chat.id, answer,
                     reply_markup=ids_keyboard, parse_mode="HTML")


@bot.message_handler(func=lambda mess: mess.reply_to_message is not None and
                     mess.reply_to_message.from_user.username == "Spbu4UBot" and
                     mess.reply_to_message.text == "Напиши мне что-нибудь:",
                     content_types=["text"])
def users_callback_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    bot.forward_message(my_id, message.chat.id, message.message_id)
    bot.send_message(message.chat.id, "Записал", reply_markup=main_keyboard,
                     reply_to_message_id=message.message_id)


@bot.message_handler(func=lambda mess:
                     mess.text == emoji["arrows_counterclockwise"],
                     content_types=["text"])
def group_templates_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = ""
    groups = func.get_templates(message.chat.id)
    group_title = func.get_current_group(message.chat.id)["title"]
    answer += "Текущая группа: <b>{0}</b>\n".format(group_title)
    last_row = ["Отмена", "Сохранить"]
    inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    if len(groups) == 0:
        answer += "Нет шаблонов групп, но ты можешь сохранить текущую\n"
    else:
        answer += "Выбери группу:"
        inline_keyboard.add(
            *[telebot.types.InlineKeyboardButton(
                text=name, callback_data=str(groups[name]))
                for name in groups.keys()]
        )
        if group_title in groups.keys():
            last_row = ["Отмена", "Удалить"]
    inline_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
            for name in last_row]
    )
    inline_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Сменить группу"]]
    )
    bot.send_message(message.chat.id, answer, reply_markup=inline_keyboard,
                     parse_mode="HTML")


@bot.message_handler(func=lambda mess: mess.text == "Скул"
                     and mess.chat.id == my_id,
                     content_types=["text"])
def schedule_update_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    tic = time.time()
    schedule_update()
    toc = time.time() - tic
    answer = "Done\nWork time: {0}".format(toc)
    bot.reply_to(message, answer)


@bot.message_handler(func=lambda mess: mess.text == emoji["bust_in_silhouette"],
                     content_types=["text"])
def educator_schedule_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Введи Фамилию преподавателя: <i>(и И. О.)</i>"
    markup = telebot.types.ForceReply(False)
    bot.send_message(message.chat.id, answer, reply_markup=markup,
                     parse_mode="HTML")


@bot.message_handler(func=lambda mess: mess.reply_to_message is not None and
                     mess.reply_to_message.from_user.username == "Spbu4UBot" and
                     "Введи Фамилию преподавателя:" in
                     mess.reply_to_message.text,
                     content_types=["text"])
def write_educator_name_handler(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = ""
    name = message.text.strip(". ")
    if not func.is_correct_educator_name(name):
        answer = "Недопустимые символы"
        schedule_keyboard = telebot.types.ReplyKeyboardMarkup(True)
        schedule_keyboard.row("Сегодня", "Завтра", "Неделя")
        schedule_keyboard.row(emoji["back"], emoji["bust_in_silhouette"],
                              emoji["arrows_counterclockwise"],
                              emoji["alarm_clock"])
        bot.send_message(message.chat.id, answer,
                         reply_markup=schedule_keyboard)
        return
    url = "https://timetable.spbu.ru/api/v1/educators/search/{0}".format(name)
    request = requests.get(url)
    request_code = request.status_code
    educators_data = request.json() if request_code == 200 else {}

    if request_code != 200 or educators_data["Educators"] is None or len(
            educators_data["Educators"]) == 0:
        answer = "Никого не найдено"
        schedule_keyboard = telebot.types.ReplyKeyboardMarkup(True)
        schedule_keyboard.row("Сегодня", "Завтра", "Неделя")
        schedule_keyboard.row(emoji["back"], emoji["bust_in_silhouette"],
                              emoji["arrows_counterclockwise"],
                              emoji["alarm_clock"])
        bot.send_message(message.chat.id, answer,
                         reply_markup=schedule_keyboard)
    elif len(educators_data["Educators"]) > 200:
        answer = "Слишком много преподавателей\n" \
                 "Пожалуйста, <b>уточни</b>"
        bot.send_message(message.chat.id, answer, parse_mode="HTML")
        answer = "Введи Фамилию преподавателя: <i>(и И. О.)</i>"
        markup = telebot.types.ForceReply(False)
        bot.send_message(message.chat.id, answer, reply_markup=markup,
                         parse_mode="HTML")
    else:
        schedule_keyboard = telebot.types.ReplyKeyboardMarkup(True)
        schedule_keyboard.row("Сегодня", "Завтра", "Неделя")
        schedule_keyboard.row(emoji["back"], emoji["bust_in_silhouette"],
                              emoji["arrows_counterclockwise"],
                              emoji["alarm_clock"])
        bot.send_message(message.chat.id, "Готово!",
                         reply_markup=schedule_keyboard)

        educators_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        educators_keyboard.add(
            *[telebot.types.InlineKeyboardButton(text=educator["DisplayName"],
                                                 callback_data=str(
                                                     educator["Id"]))
              for educator in educators_data["Educators"]])
        educators_keyboard.row(telebot.types.InlineKeyboardButton(
            text="Отмена", callback_data="Отмена"))
        answer = "{0} Найденные преподаватели:\n\n".format(
            emoji["mag_right"]) + answer
        bot.send_message(message.chat.id, answer,
                         reply_markup=educators_keyboard, parse_mode="HTML")


@bot.message_handler(func=lambda mess: True, content_types=["text"])
def other_text_handler(message):
    # logger.info(message)
    bot.send_chat_action(message.chat.id, "typing")
    answer = "Не понимаю"
    bot.send_message(message.chat.id, answer)


"""
        Callback query handlers
"""


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Полное ИНФО")
def show_full_info(call_back):
    inline_keyboard = telebot.types.InlineKeyboardMarkup()
    inline_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Краткое ИНФО"]])
    answer = full_info_answer
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          disable_web_page_preview=True,
                          reply_markup=inline_keyboard)
    inline_answer = "Много текста " + emoji["arrow_up"]
    bot.answer_callback_query(call_back.id, inline_answer, cache_time=1)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Краткое ИНФО")
def show_briefly_info(call_back):
    inline_keyboard = telebot.types.InlineKeyboardMarkup()
    inline_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Полное ИНФО"]])
    answer = briefly_info_answer
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          disable_web_page_preview=True,
                          reply_markup=inline_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data in week_day_number.keys() or
                            call_back.data == "Вся неделя")
def select_week_day_schedule_handler(call_back):
    day = ""
    if call_back.data == "Вся неделя":
        day += "Неделя"
    else:
        day += [item[0] for item in week_day_titles.items() if
                item[1] == call_back.data][0]
    answer = "Расписание на: <i>{0}</i>\n".format(day)
    week_type_keyboard = telebot.types.InlineKeyboardMarkup()
    week_type_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Текущее", "Следующее"]]
    )
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          reply_markup=week_type_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            "Расписание на: Неделя" in call_back.message.text)
def all_week_schedule_handler(call_back):
    user_id = call_back.message.chat.id
    bot_msg = call_back.message
    if call_back.data == "Текущее":
        json_week = func.get_json_week_data(user_id)
    else:
        bot_msg = bot.edit_message_text(text="Загрузка\U00002026",
                                        chat_id=user_id,
                                        message_id=call_back.message.message_id)
        json_week = func.get_json_week_data(user_id, next_week=True)
    inline_answer = json_week["WeekDisplayText"]
    bot.answer_callback_query(call_back.id, inline_answer, cache_time=1)
    if len(json_week["Days"]):
        for day in json_week["Days"]:
            full_place = func.is_full_place(call_back.message.chat.id)
            answer = func.create_schedule_answer(day, full_place,
                                                 call_back.message.chat.id)
            if "Выходной" in answer:
                continue
            if json_week["Days"].index(day) == 0:
                try:
                    bot.edit_message_text(text=answer,
                                          chat_id=user_id,
                                          message_id=bot_msg.message_id,
                                          parse_mode="HTML")
                except telebot.apihelper.ApiException:
                    func.send_long_message(bot, answer, user_id)
            else:
                func.send_long_message(bot, answer, user_id)
    else:
        answer = "{0} Выходная неделя".format(emoji["sleep"])
        bot.edit_message_text(text=answer,
                              chat_id=user_id,
                              message_id=bot_msg.message_id)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Текущее" or
                            call_back.data == "Следующее")
def week_day_schedule_handler(call_back):
    bot_msg = call_back.message
    is_next_week = False
    iso_day_date = list((datetime.today() + server_timedelta).isocalendar())
    if iso_day_date[2] == 7:
        iso_day_date[1] += 1
    if call_back.data == "Следующее":
        bot_msg = bot.edit_message_text(text="Загрузка\U00002026",
                                        chat_id=call_back.message.chat.id,
                                        message_id=call_back.message.message_id)
        iso_day_date[1] += 1
        is_next_week = True
    iso_day_date[2] = week_day_number[
        week_day_titles[call_back.message.text.split(": ")[-1]]]
    day_date = func.date_from_iso(iso_day_date)
    json_day = func.get_json_day_data(call_back.message.chat.id, day_date,
                                      next_week=is_next_week)
    full_place = func.is_full_place(call_back.message.chat.id)
    answer = func.create_schedule_answer(json_day, full_place,
                                         call_back.message.chat.id)
    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=bot_msg.message_id,
                              parse_mode="HTML")
    except telebot.apihelper.ApiException:
        func.send_long_message(bot, answer, call_back.message.chat.id)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Подписаться")
def sending_on_handler(call_back):
    func.set_sending(call_back.message.chat.id, True)
    answer = "{0} Рассылка <b>активирована</b>\nЖди рассылку в 21:00" \
             "".format(emoji["mailbox_on"])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Отписаться")
def sending_off_handler(call_back):
    func.set_sending(call_back.message.chat.id, False)
    answer = "{0} Рассылка <b>отключена</b>".format(emoji["mailbox_off"])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Обновить")
def update_yandex_handler(call_back):
    from_to_stations = call_back.message.text.split("\n\n")[0].split(" => ")
    from_station_title = from_to_stations[0]
    to_station_title = from_to_stations[1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]

    server_datetime = datetime.today() + server_timedelta
    data = get_yandex_timetable_data(from_station, to_station, server_datetime)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if data["is_tomorrow"]:
        inline_answer = emoji["warning"] + " На сегодня нет электричек"
        bot.answer_callback_query(call_back.id, inline_answer, cache_time=2)
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Оставшиеся", "Обновить"]])

    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=update_keyboard)
    except telebot.apihelper.ApiException:
        pass
    finally:
        inline_answer = emoji["check_mark"] + " Обновлено"
        bot.answer_callback_query(call_back.id, inline_answer, cache_time=1)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Оставшиеся")
def more_suburbans_handler(call_back):
    from_to_stations = call_back.message.text.split("\n\n")[0].split(" => ")
    from_station_title = from_to_stations[0]
    to_station_title = from_to_stations[1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]
    server_datetime = datetime.today() + server_timedelta
    data = get_yandex_timetable_data(from_station, to_station, server_datetime,
                                     limit=100)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if data["is_tomorrow"]:
        inline_answer = emoji["warning"] + " На сегодня нет электричек"
        bot.answer_callback_query(call_back.id, inline_answer, cache_time=2)
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Ближайшие", "Обновить"]])

    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=update_keyboard)
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Ближайшие")
def less_suburbans_handler(call_back):
    from_to_stations = call_back.message.text.split("\n\n")[0].split(" => ")
    from_station_title = from_to_stations[0]
    to_station_title = from_to_stations[1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]
    server_datetime = datetime.today() + server_timedelta
    data = get_yandex_timetable_data(from_station, to_station, server_datetime)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if data["is_tomorrow"]:
        inline_answer = emoji["warning"] + " На сегодня нет электричек"
        bot.answer_callback_query(call_back.id, inline_answer, cache_time=2)
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Оставшиеся", "Обновить"]])

    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=update_keyboard)
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Все на завтра")
def all_tomorrow_suburbans_handler(call_back):
    from_to_stations = call_back.message.text.split("\n\n")[0].split(" => ")
    from_station_title = from_to_stations[0]
    to_station_title = from_to_stations[1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]

    server_datetime = datetime.combine(
        (datetime.today() + timedelta(days=1)).date(), dt_time())

    data = get_yandex_timetable_data(from_station, to_station, server_datetime,
                                     limit=100)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    update_keyboard.row(*[telebot.types.InlineKeyboardButton(
        text=name, callback_data=name) for name in ["Самые ранние"]])

    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=update_keyboard)
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Самые ранние")
def early_tomorrow_suburbans_handler(call_back):
    from_to_stations = call_back.message.text.split("\n\n")[0].split(" => ")
    from_station_title = from_to_stations[0]
    to_station_title = from_to_stations[1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]

    server_datetime = datetime.combine(
        (datetime.today() + timedelta(days=1)).date(), dt_time())

    data = get_yandex_timetable_data(from_station, to_station, server_datetime,
                                     limit=5)
    answer = data["answer"]
    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    update_keyboard.row(*[telebot.types.InlineKeyboardButton(
        text=name, callback_data=name) for name in ["Все на завтра"]])
    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=update_keyboard)
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.message.text == "Выбери начальную "
                                                      "станцию:")
def start_station_handler(call_back):
    answer = "Начальная: <b>{0}</b>\nВыбери конечную станцию:".format(
        call_back.data)
    end_station_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for station_title in all_stations_const:
        if station_title == call_back.data:
            continue
        end_station_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in [station_title]])
    end_station_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Изменить начальную"]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=end_station_keyboard,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Изменить начальную")
def change_start_station_handler(call_back):
    answer = "Выбери начальную станцию:"
    start_station_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for station_title in all_stations_const:
        start_station_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in [station_title]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=start_station_keyboard)


@bot.callback_query_handler(func=lambda call_back: "Выбери конечную станцию:"
                                                   in call_back.message.text)
def end_station_handler(call_back):
    from_station_title = call_back.message.text.split("\n")[0].split(": ")[-1]
    to_station_title = call_back.data
    answer = "Начальная: <b>{0}</b>\nКончная: <b>{1}</b>\nВыбери день:".format(
        from_station_title, to_station_title)
    day_keyboard = telebot.types.InlineKeyboardMarkup(True)
    day_keyboard.row(*[telebot.types.InlineKeyboardButton(
        text=name, callback_data=name) for name in ["Сегодня", "Завтра"]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=day_keyboard,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back: "Выбери день:"
                                                   in call_back.message.text)
def build_trail_handler(call_back):
    from_station_title = call_back.message.text.split("\n")[0].split(": ")[-1]
    to_station_title = call_back.message.text.split("\n")[1].split(": ")[-1]
    from_station = all_stations[from_station_title]
    to_station = all_stations[to_station_title]

    if call_back.data == "Завтра":
        server_datetime = datetime.combine(
            (datetime.today() + timedelta(days=1)).date(), dt_time())
        limit = 7
    else:
        server_datetime = datetime.today() + server_timedelta
        limit = 3

    data = get_yandex_timetable_data(from_station, to_station, server_datetime,
                                     limit)
    answer = data["answer"]

    update_keyboard = telebot.types.InlineKeyboardMarkup(True)
    if call_back.data == "Завтра" or data["is_tomorrow"]:
        if data["is_tomorrow"]:
            inline_answer = emoji["warning"] + " На сегодня нет электричек"
            bot.answer_callback_query(call_back.id, inline_answer, cache_time=2)
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Все на завтра"]])
    else:
        update_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name)
            for name in ["Оставшиеся", "Обновить"]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=update_keyboard,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Домашняя")
def home_station_handler(call_back):
    answer = "Выбери домашнюю станцию:"
    stations_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for station_title in all_stations_const:
        if station_title in ("Старый Петергоф",
                             "Университетская (Университет)"):
            continue
        stations_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in [station_title]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=stations_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.message.text == "Выбери домашнюю "
                                                      "станцию:")
def change_home_station_handler(call_back):
    answer = "Домашняя станция изменена на <b>{0}</b>".format(call_back.data)
    func.change_home_station(call_back.message.chat.id, call_back.data)
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Университетская")
def univer_station_handler(call_back):
    stations = ("Старый Петергоф", "Университетская (Университет)")
    answer = "Изменить станцию <i>{0}</i> на <b>{1}</b>?"
    if func.is_univer(call_back.message.chat.id):
        answer = answer.format(stations[1], stations[0])
    else:
        answer = answer.format(stations[0], stations[1])
    inline_keyboard = telebot.types.InlineKeyboardMarkup(True)
    inline_keyboard.row(*[telebot.types.InlineKeyboardButton(
            text=name, callback_data=name) for name in ["Отмена", "Изменить"]])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=inline_keyboard,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Изменить" and
                            "Изменить станцию" in call_back.message.text)
def change_univer_station_handler(call_back):
    answer = "Используется <b>{0}</b>"
    if func.is_univer(call_back.message.chat.id):
        is_univer = 0
        station = "Старый Петергоф"
    else:
        is_univer = 1
        station = "Университетская (Университет)"
    func.change_univer_station(call_back.message.chat.id, is_univer)
    bot.edit_message_text(text=answer.format(station),
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Полностью")
def full_place_on_handler(call_back):
    func.set_full_place(call_back.message.chat.id, True)
    answer = "Теперь адрес отображается <b>полностью</b>"
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Аудитория")
def full_place_off_handler(call_back):
    func.set_full_place(call_back.message.chat.id, False)
    answer = "Теперь отображается <b>только аудитория</b>"
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Другой день")
def another_day_handler(call_back):
    answer = "Выбери день, когда есть это занятие:"
    json_week_data = func.get_json_week_data(my_id)
    days = json_week_data["Days"]
    days_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for day in days:
        days_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
              for name in [day["DayString"].split(", ")[0].capitalize()]])
    days_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Отмена"]])
    bot.edit_message_text(text=answer, chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          reply_markup=days_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data in week_day_titles.keys())
def select_day_handler(call_back):
    iso_day_date = list((datetime.today() + server_timedelta).isocalendar())
    if iso_day_date[2] == 7:
        iso_day_date[1] += 1
    iso_day_date[2] = week_day_number[week_day_titles[call_back.data]]
    day_date = func.date_from_iso(iso_day_date)
    json_day = func.get_json_day_data(call_back.message.chat.id, day_date)
    full_place = func.is_full_place(call_back.message.chat.id)
    day_data = func.create_schedule_answer(json_day, full_place, personal=False)
    answer = "Полное раписание на:" + day_data[1:] + "Выбери занятие:"
    events_keyboard = telebot.types.InlineKeyboardMarkup(True)
    events = day_data.split("\n\n")[1:-1]
    for num, event in enumerate(events, start=1):
        event_name = event.split("\n")[1][3:-4].split(" - ")
        button_text = "{0}. {1} - {2}".format(num, event_name[0],
                                              event_name[-1].split(". ")[-1])
        events_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
              for name in [button_text[:32]]])
    events_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Отмена", "Другой день"]]
    )
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          reply_markup=events_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Отмена")
def cancel_handler(call_back):
    answer = "Отмена"
    bot.edit_message_text(text=answer, chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id)


@bot.callback_query_handler(func=lambda call_back:
                            "Выбери занятие:" in call_back.message.text)
def select_lesson_handler(call_back):
    answer = "Доступные занятия "
    answer += call_back.message.text.split("\n\n")[0][17:] + "\n\n"
    events = call_back.message.text.split("\n\n")[1:-1]
    chosen_event = events[int(call_back.data.split(". ")[0]) - 1].split("\n")[1]
    days_keyboard = telebot.types.InlineKeyboardMarkup(True)
    for event in events:
        if event.split("\n")[1] != chosen_event:
            continue
        event_data = event.split("\n")
        answer += "{0}\n<b>{1}</b>\n{2}\n\n".format(event_data[0],
                                                    event_data[1],
                                                    "\n".join(event_data[2:]))
    day_title = answer.split("\n\n")[0].split(": ")[-1].split(", ")[0]
    if day_title == "Понедельник" or day_title == "Вторник" or \
                    day_title == "Четверг":
        day_title += "и"
    else:
        day_title = day_title[:-1] + "ы"
    days_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Все {0}".format(day_title.lower())]])
    days_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
          for name in ["Отмена", "Все дни"]])
    answer += "Выбери дни для скрытия занятия:"
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          reply_markup=days_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            "Выбери дни для скрытия занятия:" in
                            call_back.message.text)
def select_time_handler(call_back):
    answer = call_back.message.text.split("\n\n")[0] + "\n\n"

    times_keyboard = telebot.types.InlineKeyboardMarkup(True)
    events = call_back.message.text.split("\n\n")[1:-1]
    for event in events:
        event_data = event.split("\n")
        answer += "{0}\n<b>{1}</b>\n{2}\n\n".format(event_data[0],
                                                    event_data[1],
                                                    "\n".join(event_data[2:]))
        times_keyboard.row(
            *[telebot.types.InlineKeyboardButton(text=name, callback_data=name)
              for name in [event_data[0].split(emoji["clock"])[-1].split(
                    emoji["warning"])[0].strip()]])
    times_keyboard.row(
        *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
          name in ["Отмена", "Любое время"]])
    answer += "День: <b>{0}</b>\n\nВыбери время, в которе скрывать:".format(
        call_back.data)
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML",
                          reply_markup=times_keyboard)


@bot.callback_query_handler(func=lambda call_back:
                            "Выбери время, в которе скрывать:" in
                            call_back.message.text)
def confirm_hide_lesson_handler(call_back):
    data = call_back.message.text.split("\n\n")
    hide_event_data = data[1].split("\n")[1].split(" - ")
    hide_day = data[-2].split(": ")[1]
    hide_time = call_back.data
    if hide_event_data[0] in subject_short_type_revert.keys():
        hide_event_data[0] = subject_short_type_revert[hide_event_data[0]]
    if hide_day == "Все дни":
        hide_day = "all"
    else:
        hide_day = data[0].split(": ")[1].split(", ")[0].lower()
    if hide_time == "Любое время":
        hide_time = "all"

    func.insert_skip(hide_event_data, hide_day, hide_time,
                     call_back.message.chat.id)
    answer = "<b>Занятие скрыто:</b>\n{0}, {1}".format(hide_event_data[1],
                                                       hide_event_data[0])
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Вернуть всё")
def return_all(call_back):
    sql_con = sqlite3.connect("Bot_db")
    cursor = sql_con.cursor()
    cursor.execute("""DELETE FROM skips 
                      WHERE user_id = ?""", (call_back.message.chat.id, ))
    sql_con.commit()
    cursor.close()
    sql_con.close()

    answer = "Все занятия возвращены"
    bot.edit_message_text(text=answer, chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id)


@bot.callback_query_handler(func=lambda call_back:
                            "Выбери то, которое хочешь вернуть:" in
                            call_back.message.text)
def return_lesson_handler(call_back):
    lesson_id = call_back.data.split(" - ")[0]
    events = call_back.message.text.split("\n\n")[1:-1]
    lesson_title = lesson_type = ""
    for event in events:
        if event.split("\n")[0].split(": ")[1] == lesson_id:
            lesson_title = event.split("\n")[1].split(": ")[1]
            lesson_type = event.split("\n")[2].split(": ")[1]
            break
    sql_con = sqlite3.connect("Bot_db")
    cursor = sql_con.cursor()
    cursor.execute("""DELETE FROM skips 
                      WHERE user_id = ?
                        AND lesson_id = ?""",
                   (call_back.message.chat.id, lesson_id))
    sql_con.commit()
    cursor.close()
    sql_con.close()
    answer = "<b>Занятие возвращено:</b>\n{0}, {1}".format(lesson_title,
                                                           lesson_type)
    bot.edit_message_text(text=answer, chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Статистика")
def statistics_handler(call_back):
    data = func.get_rate_statistics()
    if data is None:
        answer = "Пока что нет оценок."
    else:
        rate = emoji["star"] * round(data[0])
        answer = "Средняя оценка: {0}\n{1} ({2})".format(
                                            round(data[0], 1), rate, data[1])
    if call_back.message.chat.id == my_id:
        admin_data = func.get_statistics_for_admin()
        admin_answer = "\n\nКолличество пользователей: {0}\n" \
                       "Колличество групп: {1}\nКолличество пользователей с " \
                       "активной рассылкой: {2}".format(
                                    admin_data["count_of_users"],
                                    admin_data["count_of_groups"],
                                    admin_data["count_of_sending"])
        bot.send_message(my_id, admin_answer)
    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML")
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Связь")
def feedback_handler(call_back):
    markup = telebot.types.ForceReply(False)
    try:
        bot.edit_message_text(text="Обратная связь",
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id)
    except telebot.apihelper.ApiException:
        pass
    finally:
        answer = "Напиши мне что-нибудь:"
        bot.send_message(call_back.message.chat.id, answer,
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data in ["1", "2", "3", "4", "5"])
def set_rate_handler(call_back):
    rate = call_back.data
    answer = ""
    func.set_rate(call_back.message.chat.id, rate)
    if rate == "5":
        answer += "{0} Пятёрка! Супер! Спасибо большое!".format(emoji["smile"])
    elif rate == "4":
        answer += "{0} Стабильная четверочка. Спасибо!".format(emoji["halo"])
    elif rate == "3":
        answer += "{0} Удовлетворительно? Ничего... тоже оценка. " \
                  "Буду стараться лучше.".format(emoji["cold_sweat"])
    elif rate == "2":
        answer += "{0} Двойка? Быть может, я могу что-то исправить? " \
                  "Сделать лучше?\n\nОпиши проблему " \
                  "<a href='https://t.me/eeonedown'>разработчику</a>, " \
                  "и вместе мы ее решим!".format(emoji["disappointed"])
    elif rate == "1":
        answer += "{0} Единица? Быть может, я могу что-то исправить? " \
                  "Сделать лучше?\n\nОпиши проблему " \
                  "<a href='https://t.me/eeonedown'>разработчику</a>, " \
                  "и вместе мы ее решим!".format(emoji["disappointed"])
    user_rate = func.get_user_rate(call_back.message.chat.id)
    rate_keyboard = telebot.types.InlineKeyboardMarkup(row_width=5)
    rate_keyboard.add(*[telebot.types.InlineKeyboardButton(
        text=emoji["star2"] if user_rate < count_of_stars else emoji["star"],
        callback_data=str(count_of_stars))
        for count_of_stars in (1, 2, 3, 4, 5)])
    rate_keyboard.add(
        *[telebot.types.InlineKeyboardButton(text=name,
                                             callback_data=name)
          for name in ["Связь", "Статистика"]])
    try:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML",
                              reply_markup=rate_keyboard,
                              disable_web_page_preview=True)
    except telebot.apihelper.ApiException:
        pass


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Сохранить")
def save_current_group_handler(call_back):
    user_id = call_back.message.chat.id
    group_data = func.get_current_group(user_id)
    func.save_group(group_data["id"], user_id)
    answer = "Группа <b>{0}</b> сохранена".format(group_data["title"])
    bot.edit_message_text(text=answer,
                          chat_id=user_id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Удалить")
def delete_current_group_handler(call_back):
    user_id = call_back.message.chat.id
    group_data = func.get_current_group(user_id)
    func.delete_group(group_data["id"], user_id)
    answer = "Группа <b>{0}</b> удалена".format(group_data["title"])
    bot.edit_message_text(text=answer,
                          chat_id=user_id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back:
                            call_back.data == "Сменить группу")
def change_group_handler(call_back):
    answer = "{0}\nДля отмены используй /home".format(call_back.data)
    bot.edit_message_text(text=answer,
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")
    call_back.message.text = call_back.data
    start_handler(call_back.message)
    return


@bot.callback_query_handler(func=lambda call_back:
                            "Выбери группу:" in call_back.message.text)
def change_template_group_handler(call_back):
    answer = "Группа успешно изменена на <b>{0}</b>"
    chosen_group_id = int(call_back.data)
    sql_con = sqlite3.connect("Bot_db")
    cursor = sql_con.cursor()
    cursor.execute("""SELECT alias, json_week_data
                      FROM groups_data
                      WHERE id = ?""", (chosen_group_id, ))
    data = cursor.fetchone()
    chosen_group_alias = data[0]
    chosen_group_title = json.loads(data[1])["StudentGroupDisplayName"][7:]
    cursor.execute("""UPDATE user_data 
                      SET alias = ?, group_id = ?
                      WHERE id = ?""",
                   (chosen_group_alias, chosen_group_id,
                    call_back.message.chat.id))
    sql_con.commit()
    cursor.close()
    sql_con.close()
    bot.edit_message_text(text=answer.format(chosen_group_title),
                          chat_id=call_back.message.chat.id,
                          message_id=call_back.message.message_id,
                          parse_mode="HTML")


@bot.callback_query_handler(func=lambda call_back: "Найденные преподаватели:"
                                                   in call_back.message.text)
def select_master_id_handler(call_back):
    answer = "{0} Расписание преподавателя: <b>{1}</b>\n\n{2} {3}"
    url = "https://timetable.spbu.ru/api/v1/educators/{0}/events".format(
        call_back.data)
    educator_schedule = requests.get(url).json()
    answer = answer.format(emoji["bust_in_silhouette"],
                           educator_schedule["EducatorLongDisplayText"],
                           emoji["calendar"],
                           educator_schedule["DateRangeDisplayText"])
    if not educator_schedule["HasEvents"]:
        answer += "\n\n<i>Нет событий</i>"
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML")
    else:
        bot.edit_message_text(text=answer,
                              chat_id=call_back.message.chat.id,
                              message_id=call_back.message.message_id,
                              parse_mode="HTML")
        days = [day for day in educator_schedule["EducatorEventsDays"]
                if day["DayStudyEventsCount"]]
        for day in days:
            answer = func.create_master_schedule_answer(day)
            func.send_long_message(bot, answer, call_back.message.chat.id)


@app.route("/reset_webhook", methods=["GET", "HEAD"])
def reset_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url_base + webhook_url_path)
    return "OK", 200


@app.route("/", methods=["GET", "HEAD"])
def main_page():
    page = '<meta http-equiv="refresh" content="1;url=https://t.me/Spbu4UBot">'
    return page, 200


@app.route(webhook_url_path, methods=["POST"])
def webhook():
    if flask.request.headers.get("content-type") == "application/json":
        json_string = flask.request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        was_error = False
        tic = time.time()
        try:
            bot.process_new_updates([update])
        except Exception as err:
            answer = "Кажется, произошла ошибка.\n" \
                     "Возможно, информация по этому поводу есть в нашем " \
                     "канале - @Spbu4u_news\nИ ты всегда можешь связаться с " \
                     "<a href='https://t.me/eeonedown'>разработчиком</a>"
            was_error = True
            was_sent = False
            if update.message is not None:
                try:
                    bot.send_message(update.message.chat.id,
                                     answer,
                                     disable_web_page_preview=True,
                                     parse_mode="HTML")
                    was_sent = True
                except telebot.apihelper.ApiException as ApiExcept:
                    json_err = json.loads(ApiExcept.result.text)
                    if json_err["description"] == "Forbidden: bot was " \
                                                  "blocked by the user":
                        func.delete_user(update.message.chat.id)
                        logging.info("USER LEFT {0}".format(
                            update.message.chat.id))
                    else:
                        logging.info("ERROR: {0}".format(
                            json_err["description"]))
            else:
                pass
            bot.send_message(my_id,
                             str(err) + "\n\nWas sent: {0}".format(was_sent),
                             disable_notification=True)
        finally:
            func.write_log(update, time.time() - tic, was_error)
        return "OK", 200
    else:
        flask.abort(403)


if __name__ == '__main__':
    '''
    use test_token for local testing
    or don't forget to reset webhook
    '''
    bot.remove_webhook()
    bot.polling(none_stop=True, interval=0)
