from telebot import *
import sqlite3
from auth import auth
from info import *
from draw import *
from datetime import date, timedelta
import asyncio
from time import sleep

bot = TeleBot()
conn = sqlite3.connect("database/db.db3", check_same_thread=False)
cursor = conn.cursor()


def checkNewestGrades(user_id):
    oldGradeListFile = open(f'C:\\Users\\retys\\PycharmProjects\\pythonProject1\\gradelists\\{user_id}.txt', 'r+')
    subDomain = getMainData(user_id)[0]
    if oldGradeListFile.readlines() == []:
        session = authFromDB(user_id)
        if session is None:
            return
        gradeList = getGradeList(subDomain, session['session'], 'latest')['themes']
        oldGradeListFile.write(gradeList)
        del gradeList
        del session
    oldGradeListFile.close()
    await asyncio.sleep(600)
    newSession = authFromDB(user_id)
    if newSession is None:
        return
    oldGradeList = open(f'C:\\Users\\retys\\PycharmProjects\\pythonProject1\\gradelists\\{user_id}.txt', 'r').read()
    newGradeList = getGradeList(subDomain, newSession['session'], 'latest')['themes']
    text = 'Появились новые оценки:\n'
    for lesson, marks in newGradeList.items():
        while {"mark": None, "date": None, "isMark": False} in marks:
            marks.remove({"mark": None, "date": None, "isMark": False})
        while {"mark": None, "date": None, "isMark": False} in oldGradeList[lesson]:
            oldGradeList[lesson].remove({"mark": None, "date": None, "isMark": False})
        change = []
        for mark in marks:
            if mark not in oldGradeList[lesson]:
                change.append(mark)
        if not change:
            continue
        change = [f'{mark["mark"]} за {mark["date"]}' for mark in change]
        text += f"{lesson}: {', '.join(change)}\n"
    oldGradeListFile.write(getGradeList(subDomain, newSession['session'], 'latest')['themes'])
    await bot.send_message(getChatID(user_id), text)


def authFromDB(user_id):
    data = getMainData(user_id)
    subd, data = data[0], {"username": data[1], "password": data[2]}
    result = auth(subd, data)
    chat_id = getChatID(user_id)
    if "error_msg" in result.keys():
        if result["error_msg"] != "Неверный домен школы":
            cursor.execute(f"DELETE FROM db WHERE user_id='{user_id}';")
            bot.send_message(
                chat_id,
                "Oops! Что-то пошло не так. Пожалуйста, пройдите авторизацию заново, написав /start.",
            )
    else:
        return result


def pushDB(uid: int, username: str, subd: str, log: str, password: str, chat_id: int):
    cursor.execute(
        "INSERT INTO db (user_id, username, subdomain, login, password, chat_id) VALUES (?, ?, ?, ?, ?, ?)",
        (uid, username, subd, log, password, chat_id),
    )
    conn.commit()


def markupMainMenu():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "Получить расписание на неделю", callback_data="getjournal_0"
        )
    )
    markup.add(
        types.InlineKeyboardButton("Получить табель оценок", callback_data="getgl_prev")
    )

    return markup


def toFixed(num_obj, digits=0):
    return f"{num_obj:.{digits}f}"


def getMainData(user_id):
    return [
        cursor.execute(
            f"SELECT subdomain FROM db WHERE user_id='{user_id}'"
        ).fetchone()[0],
        cursor.execute(f"SELECT login FROM db WHERE user_id='{user_id}'").fetchone()[0],
        cursor.execute(f"SELECT password FROM db WHERE user_id='{user_id}'").fetchone()[0],
    ]


def getChatID(user_id):
    return cursor.execute(f"SELECT chat_id FROM db WHERE user_id='{user_id}'").fetchone()[0]


@bot.message_handler(commands=["start"])
@bot.callback_query_handler(
    func=lambda call: call.data in ("go_back", "go_back_journal")
)
def startMsg(msg):
    if type(msg) == types.CallbackQuery:
        chat_id = msg.message.chat.id
        user_id = msg.message.json["chat"]["id"]
        message_id = msg.message.json["message_id"]
        if msg.data == "go_back_journal":
            bot.delete_message(chat_id, message_id)
    else:
        chat_id = msg.chat.id
        user_id = msg.from_user.id
        message_id = msg.id

    if not cursor.execute(
        f"SELECT user_id FROM db WHERE user_id='{user_id}'"
    ).fetchone():
        msg = bot.send_message(
            chat_id,
            "Для работы с eljur требуется авторизация и домен школы (arh-licey для arh-licey.eljur.ru)\n"
            "Введите субдомен:",
        )
        bot.register_next_step_handler(msg, getSub)
    else:
        data = getMainData(user_id)
        session = authFromDB(user_id)
        if session is None:
            return
        info = getInfo(data[0], session["session"])
        surname, name = info["Фамилия"], info["Имя"]
        text = f"Приветствую, {surname} {name}."
        if type(msg) == types.CallbackQuery and msg.data != "go_back_journal":
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markupMainMenu(),
            )
        else:
            bot.send_message(chat_id, text, reply_markup=markupMainMenu())





@bot.callback_query_handler(func=lambda call: call.data[:11] == "getjournal_")
def getJournal_Main(call):
    message_id = call.message.json["message_id"]
    chat_id = call.message.chat.id
    week = int(call.data.split("_")[1])
    datetoday = date.today() + timedelta(days=7 * week)
    start_date = datetoday - timedelta(datetoday.weekday())
    end_date = start_date + timedelta(days=6)
    markup = types.InlineKeyboardMarkup(row_width=8)
    markup.add(
        types.InlineKeyboardButton(
            "← Предыдущая неделя", callback_data=f"getjournal_{week - 1}"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Понедельник, " + str(start_date), callback_data=f"getjournalday_1_{week}"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Вторник, " + str(start_date + timedelta(days=1)),
            callback_data=f"getjournalday_2_{week}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Среда, " + str(start_date + timedelta(days=2)),
            callback_data=f"getjournalday_3_{week}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Четверг, " + str(start_date + timedelta(days=3)),
            callback_data=f"getjournalday_4_{week}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Пятница, " + str(start_date + timedelta(days=4)),
            callback_data=f"getjournalday_5_{week}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Суббота, " + str(start_date + timedelta(days=5)),
            callback_data=f"getjournalday_6_{week}",
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            "Следующая неделя →", callback_data=f"getjournal_{week + 1}"
        )
    )
    markup.add(types.InlineKeyboardButton("Вернуться назад", callback_data="go_back"))
    if call.data[-1] != "j":
        bot.delete_message(chat_id, call.message.json["message_id"])
    bot.send_message(
        chat_id,
        f"Текущая неделя - c {start_date} по {end_date}.\nВыберите день или переключите неделю",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data[:14] == "getjournalday_")
def getJournal_Day(call):
    chat_id = call.message.chat.id
    user_id = call.message.json["chat"]["id"]
    data = getMainData(user_id)
    session = authFromDB(user_id)
    if session is None:
        return
    journal = getJournal(
        data[0],
        session["session"],
        week=int(call.data.split("_")[2]),
    )
    drawJournal(journal[call.data.split("_")[1]], user_id)
    bot.delete_message(chat_id, call.message.json["message_id"])
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "Выбрать другой день", callback_data="getjournal_0_j"
        )
    )
    markup.add(
        types.InlineKeyboardButton("Вернуться назад", callback_data="go_back_journal")
    )
    bot.send_photo(
        chat_id,
        types.InputFile(
            f"journalLists\day_{user_id}.jpg"
        ),
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "getgl_prev")
def getGradeList_Prev(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("I четверть", callback_data="getgl_1"))
    markup.add(types.InlineKeyboardButton("II четверть", callback_data="getgl_2"))
    markup.add(types.InlineKeyboardButton("III четверть", callback_data="getgl_3"))
    markup.add(types.InlineKeyboardButton("IV четверть", callback_data="getgl_4"))
    markup.add(types.InlineKeyboardButton("Вернуться назад", callback_data="go_back"))
    message_id = call.message.json["message_id"]
    chat_id = call.message.chat.id
    bot.edit_message_text(
        f"Выберите четверть",
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
    )


@bot.callback_query_handler(
    func=lambda call: call.data.split("_")[0] == "getgl"
    and call.data.split("_")[1] != "prev"
)
def getGradeList_Main(call):
    chat_id = call.message.chat.id
    user_id = call.message.json["chat"]["id"]
    data = getMainData(user_id)
    session = authFromDB(user_id)
    if session is None:
        return
    gradeList = getGradeList(data[0], session["session"], int(call.data.split("_")[1]))
    drawGradeList(gradeList, user_id)
    bot.delete_message(chat_id, call.message.json["message_id"])
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Вернуться назад", callback_data="go_back_journal")
    )
    if gradeList["themes"] is not None:
        bot.send_photo(
            chat_id,
            types.InputFile(
                f"gradeLists_out\gl_{user_id}.jpg"
            ),
            reply_markup=markup,
        )
    else:
        bot.send_message(
            chat_id,
            f"Отметки в {call.data.split('_')[1]} четверти отсутсвуют",
            reply_markup=markup,
        )


def getSub(msg):
    global subdomain
    subdomain = msg
    msg = bot.send_message(msg.chat.id, "Введите логин:")
    bot.register_next_step_handler(msg, getLog)


def getLog(msg):
    global login
    login = msg
    msg = bot.send_message(msg.chat.id, "Введите пароль:")
    bot.register_next_step_handler(msg, authFinal)


def authFinal(msg):
    authResult = auth(subdomain.text, {"username": login.text, "password": msg.text})
    if not authResult["result"]:
        bot.send_message(
            msg.chat.id, authResult["error_msg"] + "\n Пройдите авторизацию ещё раз."
        )
    else:
        pushDB(
            msg.from_user.id,
            msg.from_user.username,
            subdomain.text,
            login.text,
            msg.text,
            msg.chat.id
        )

        bot.send_message(msg.chat.id, "Авторизация прошла удачно.")
    startMsg(msg)


if __name__ == '__main__':
    bot.polling(none_stop=True)
