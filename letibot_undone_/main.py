import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import re

API_TOKEN = '7222857072:AAEYoAkgQP-jHVNz91P0fEN1zxN9slh-Uq4'

conn = sqlite3.connect("db.db3")
cursor = conn.cursor()

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))

d = {
    -1: 'Заблокирован',
    0: 'Не авторизован',
    1: 'Студент',
    2: 'Профорг',
    3: 'Староста',
    4: 'Администратор',
}

dp = Dispatcher()

class CreateUser(StatesGroup):
    question1 = State()
    question2 = State()

class EnterMessage(StatesGroup):
    msg = State()

@dp.message(CommandStart())
async def __start(message: Message):
    cursor.execute('SELECT status, [group], realname FROM users WHERE uid = ?', (message.from_user.id,))
    result = cursor.fetchall()
    if result:
        if result[0][0] == 0:
           btn = InlineKeyboardButton(text='✅ Я готов!', callback_data='proceed')
           menu = InlineKeyboardMarkup(inline_keyboard=[[btn]])
           await message.answer(f'<b>Привет, {message.from_user.full_name}</b>\n\n<em>Для использования бота необходимо уточнить данные, Вы готовы?</em>',
                                 reply_markup=menu)
        else:
            mailing = InlineKeyboardButton(text='Рассылка', callback_data='mailing')
            menu = InlineKeyboardMarkup(inline_keyboard=[[mailing]])
            await message.answer(f'<b>📂 Главное меню\n\n📯 Статус: <code>{d[result[0][0]]}</code>\n\n🧍‍♂️ Данные</b>: <code>{result[0][1]}</code>, <b>группа  </b><code>{result[0][2]}</code>', reply_markup=menu)
    else:
        cursor.execute('INSERT INTO users (uid, status, username) VALUES (?, ?, ?)', (message.from_user.id, 0, message.from_user.username if message.from_user.username is not None else ''))
        conn.commit()
        btn = InlineKeyboardButton(text='✅ Я готов!', callback_data='proceed')
        menu = InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer(f'<b>Привет, {message.from_user.full_name}</b>\n\n<em>Для использования бота необходимо уточнить данные, Вы готовы?</em>',
                                 reply_markup=menu)


@dp.callback_query(lambda c: c.data == 'proceed')
async def __proceed(callback_query: types.CallbackQuery, state: FSMContext):
        cid = callback_query.message.chat.id
        mid = callback_query.message.message_id
        await bot.edit_message_text(text = '''#️⃣ Введите номер Вашей группы''', chat_id=cid, message_id=mid)
        await state.set_state(CreateUser.question1)

@dp.callback_query(lambda c: c.data == 'go_start')
async def __mainmenu(callback_query: types.CallbackQuery):
        cid = callback_query.message.chat.id
        mid = callback_query.message.message_id
        cursor.execute('SELECT status FROM users WHERE uid = ?', (callback_query.message.from_user.id,))
        result = cursor.fetchall()
        if result:
            mailing = InlineKeyboardButton(text='Рассылка', callback_data='mailing')
            menu = InlineKeyboardMarkup(inline_keyboard=[[mailing]])
            await bot.edit_message_text(f'<b>📂 Главное меню\n\n📯 Статус: <code>{d[result[0][0]]}</code>\n\n🧍‍♂️ Данные</b>: <code>{result[0][1]}</code>, <b>группа  </b><code>{result[0][2]}</code>', reply_markup=menu, chat_id=cid, message_id=mid)

@dp.message(CreateUser.question1)
async def __q_1(message: Message, state: FSMContext):
        q_1 = message.text
        if re.fullmatch(r'\d{4}', q_1):
            await state.update_data(q1=q_1)
            await message.answer('''🔎 Введите Ваше ФИО''')
            await state.set_state(CreateUser.question2)
        else:
            btn = InlineKeyboardButton(text='⬅️ Назад', callback_data='proceed')
            menu = InlineKeyboardMarkup(inline_keyboard=[[btn]])
            await message.answer('''<b>❌ Номер группы должен состоять из 4-х цифр!</b>''', reply_markup=menu)

@dp.message(CreateUser.question2)
async def __finalauthorization(message: Message, state: FSMContext):
        q_2 = message.text
        await state.update_data(q2=q_2)
        user_data = await state.get_data()
        cursor.execute('update users set realname=?, [group]=?, status=1 where uid=? ', (user_data['q1'], user_data['q2'], message.from_user.id,))
        conn.commit()
        await message.answer('''<b>✅ Вы авторизованы.\n\n Нажмите /start для начала работы</b>''')
        await state.clear()

@dp.callback_query(lambda c: c.data == 'mailing')
async def __proceed(callback_query: types.CallbackQuery, state: FSMContext):
        cid = callback_query.message.chat.id
        mid = callback_query.message.message_id
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data='go_start')]])
        await bot.edit_message_text(f"<b>Введите сообщение:</b>", chat_id=cid, message_id=mid, reply_markup=markup)
        await state.set_state(EnterMessage.msg)

@dp.message(EnterMessage.msg)
async def __mailing(message: types.Message):
    users = cursor.execute('SELECT uid FROM users').fetchall()
    succ = 0
    errs = 0
    text = message.caption if message.photo else message.text
    photo = message.photo[-1].file_id if message.photo else None
    btn = InlineKeyboardButton(text='⬅️ Назад', callback_data='go_start')
    menu = InlineKeyboardMarkup(inline_keyboard=[[btn]])
    for user in users:
        try:
            if photo:
                await bot.send_photo(chat_id=user[0], photo=photo, caption=text)
            else:
                await bot.send_message(chat_id=user[0], text=text)
            succ += 1
        except Exception as error:
            await bot.send_message(chat_id=message.from_user.id, text=f"<b>❌ Произошла ошибка при отправкеn{str(error)}</b>")
            errs += 1
    final_text = f"<b>✅ Успешно отправлено: <code>{succ}</code></b>"
    if errs > 0:
        final_text += f"<b>❌ Не отправлено: <code>{errs}</code></b>"
    await bot.send_message(chat_id=message.from_user.id, text=final_text, reply_markup=menu)


@dp.message(Command("rating"))
async def send_rating(message: Message):
    pass


@dp.message(Command("literature"))
async def send_literature(message: Message):
    pass


@dp.message(Command("teacher"))
async def send_teacher(message: Message):
    pass


@dp.message(Command("next_couple"))
async def send_next_couple(message: Message):
    pass


@dp.message(Command("timetable"))
async def send_timetable(message: Message):
    pass


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


#test