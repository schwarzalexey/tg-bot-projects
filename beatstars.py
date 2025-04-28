import aiohttp
import asyncio
import json
import random
import os
import collections
import random
import aiofiles
from aiohttp_socks import ProxyConnector
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import TCPConnector
import certifi
import ssl
import aiosqlite
from collections import deque


class waiting_for_token(StatesGroup):
    waiting_for_token = State()

class waiting_for_paste(StatesGroup):
    waiting_for_paste = State()

user_stop_events = {}
lock = asyncio.Lock()  
checked_seller_ids = set()

async def load_checked_seller_ids() -> None:
    if os.path.exists('checked_users.txt'):
        async with aiofiles.open('checked_users.txt', mode='r') as f:
            async for line in f:
                seller_id = line.strip()
                if seller_id:
                    checked_seller_ids.add(seller_id)

async def save_seller_id(seller_id: str) -> None:
    async with aiofiles.open('checked_users.txt', mode='a') as f:
        await f.write(seller_id + '\n')


BOT_TOKEN = ''
ADMIN_CHAT = 0

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

whitelist = []

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in whitelist:

        
        result = await (await database.execute('SELECT uid FROM main WHERE uid=?', (user_id,))).fetchone()
        print(await (await database.execute('SELECT paste FROM main WHERE uid=?', (user_id,))).fetchone())


        if result is None:
            await database.execute('INSERT INTO main (uid) VALUES (?)', (user_id,))
            await database.commit()
        

        if message.chat.id == ADMIN_CHAT:
            await message.answer("🖕 Послан Нахуй 🖕")
        else:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="▶️ Start", callback_data="start_fetching")
            keyboard.button(text="⚙️ Settings", callback_data="setup")
            await message.answer("✨ BEATSTARS.com", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data == "main_menu")
async def start_command(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in whitelist:

        result = await (await database.execute('SELECT uid FROM main WHERE uid=?', (user_id,))).fetchone()
        if result is None:
            await database.execute('INSERT INTO main (uid) VALUES (?)', (user_id,))
            await database.commit()

        

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="▶️ Start", callback_data="start_fetching")
        keyboard.button(text="⚙️ Settings", callback_data="setup")
        await callback.message.answer("✨ BEATSTARS.com", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data == "setup")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 TOKEN", callback_data="setup_token")],
        [InlineKeyboardButton(text="🍝 PASTE", callback_data="setup_paste")],
        [InlineKeyboardButton(text="🔙 MENU", callback_data="main_menu")],
        
    ])
    await callback.message.answer("⚙️ **Settings**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "setup_paste")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔧 Please upload the file `paste.txt`.")
    await state.set_state(waiting_for_paste.waiting_for_paste)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "setup_token")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔧 Please upload the file `token.txt`.")
    await state.set_state(waiting_for_token.waiting_for_token)
    await callback.answer()

@dp.message(waiting_for_token.waiting_for_token)
async def process_paste(message: types.Message, state: FSMContext):
    document = message.document
    if document.file_name != 'token.txt':
        await message.answer("❌ Please upload a file named `token.txt`.")
        return
    try:
        await message.bot.download(file=document, destination=f"{message.from_user.id}token.txt")
        with open(f'{message.from_user.id}token.txt', 'r', encoding='utf-8') as f:
            paste_content = f.read()

        await database.execute('UPDATE main SET token=? WHERE uid=?', (paste_content, message.from_user.id))
        await database.commit()
        await message.answer("✅ File `token.txt `uploaded successfully.", parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Error processing the file `token.txt `: {e}", parse_mode="Markdown")

@dp.message(waiting_for_paste.waiting_for_paste)
async def process_paste(message: types.Message, state: FSMContext):
    document = message.document
    if document.file_name != 'paste.txt':
        await message.answer("❌ Please upload a file named `paste.txt`.")
        return
    try:
        await message.bot.download(file=document, destination=f"{message.from_user.id}paste.txt")
        with open(f'{message.from_user.id}paste.txt', 'r', encoding='utf-8') as f:
            paste_content = f.read()

        await database.execute('UPDATE main SET paste=? WHERE uid=?', (paste_content, message.from_user.id))
        await database.commit()
        await message.answer("✅ File `paste.txt `uploaded successfully.", parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Error processing the file `paste.txt `: {e}", parse_mode="Markdown")

@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in whitelist:
        if message.chat.id == ADMIN_CHAT:
            await message.answer("🖕 Послан Нахуй 🖕")
        else:
            if user_id not in user_stop_events:
                user_stop_events[user_id] = asyncio.Event()

            user_stop_events[user_id].set()
            await message.answer('🗿 Stopped')

@dp.callback_query(lambda c: c.data == "start_fetching")
async def start_fetching(callback_query: types.CallbackQuery):

    user_id = callback_query.from_user.id
    
    if user_id in whitelist:

        if user_id not in user_stop_events:
            user_stop_events[user_id] = asyncio.Event()
        else:
            user_stop_events[user_id].clear()

        await callback_query.message.edit_text(f"🚀🚀🚀", parse_mode="Markdown")

        
        await fetch_data(user_id)

        
async def fetch_data(user_id):

    while True:
        if user_stop_events[user_id].is_set():
            break

        url_parse = "https://nmmgzjq6qi-dsn.algolia.net/1/indexes/public_prod_inventory_track_index_bydate/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.20.0)%3B%20Browser"
        
        headers_parse = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-GB,en;q=0.9",
            "connection": "keep-alive",
            "content-type": "application/x-www-form-urlencoded",
            "host": "nmmgzjq6qi-dsn.algolia.net",
            "origin": "https://www.beatstars.com",
            "referer": "https://www.beatstars.com/",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "x-algolia-api-key": "b3513eb709fe8f444b4d5c191b63ea47",
            "x-algolia-application-id": "NMMGZJQ6QI",
        }

        params = {
            "query": "",
            "page": "0",
            "hitsPerPage": "100",
            "facets": '["*"]',
            "analytics": "true",
            "clickAnalytics": "true",
            "tagFilters": "[]",
            "facetFilters": "[]",
            "maxValuesPerFacet": "20",
            "enableABTest": "false",
            "userToken": "none",
            "filters": "",
            "ruleContexts": "[]"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url_parse, headers=headers_parse, json=params) as response:
                print(f"{user_id} = [PARSER] = status: {response.status}")
                response_data = await response.json()
                hits = response_data.get("hits", [])
                for hit in hits:
                    if user_stop_events[user_id].is_set():
                        break
                    profile = hit.get("profile", {})

                    username = profile.get("username")
                    displayName =  profile.get("displayName")
                    avatar = profile.get("avatar").get("url")
                    
                    result = await process_user(session, username, user_id)
                    if result != None:
                        username = result[0]
                        followers = result[1]
                        tracks = result[2]
                        userid = result[3]
                        i = 0
                        await bot.send_message(user_id, f"🐘 NEW USER FOUND\n\nUsername: `https://beatstars.com/{username}`\nUserid: `{userid}`\n\nFollowers: `{followers}`\nTracks: `{tracks}`", parse_mode="Markdown")
                        await asyncio.sleep(30)
                        await send_message(user_id, session, username, userid, displayName, avatar, i)
                         

        await asyncio.sleep(30) 

async def send_message(user_id, session, username, userid, displayName, avatar, i):
    
    url_create = f"https://core.prod.beatstars.net/activity/message/thread?user={userid}"
    url_send = "https://core.prod.beatstars.net/activity/message"

    token = await (await database.execute('SELECT token FROM main WHERE uid=?', (user_id,))).fetchone()


    paste = await (await database.execute('SELECT paste FROM main WHERE uid=?', (user_id,))).fetchone()

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en,en-GB;q=0.9",
        "app": "WEB_MARKETPLACE",
        "authorization": f"Bearer {str(token).replace("('", '', 1).replace("',)", '', 1)}",
        "content-type": "application/json",
        "origin": "https://www.beatstars.com",
        "referer": "https://www.beatstars.com/",
        "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    async def generate_link(session, name, avatar):
        api_url = ""
        data = {
            'api_key': '',
            'title': name,
            'service': '',
            
            'photo': avatar,
            
            'userId': user_id,
        }

        try:
            async with session.post(api_url, json=data) as req: 
                if req.status == 200:
                    response = await req.json()
                    lnk = str(response.get('message', ''))
                    return "https://beatstars.com@" + lnk.replace('https://', '', 1)
                else:
                    print(f"Ошибка HTTP: {req.status}")
                    return None
        except aiohttp.ClientError as e:
            print(f"Ошибка при соединении с API: {e}")
            return None
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            return None
    
    lnk = (await generate_link(session, displayName, avatar)).replace("shop", "𝘀𝗵𝗼𝗽", 1)

    async with session.get(url_create, headers=headers) as response:
        data = await response.json()
        
        
        chat_id = data.get("data", {}).get("id")
        

        payload = {
            "message": f"{str(paste).replace("('", '', 1).replace("',)", '', 1).replace("[LINK]", lnk, 1)}",
            "thread": f"{chat_id}"
        }

        async with session.post(url_send, headers=headers, json=payload) as response:
            data = await response.json()
            print(data)
            i += 1
            if response.status == 200:
                await bot.send_message(user_id, f"`[{i}]` ✔️  заслали биточек -> `{username}`", parse_mode="Markdown")
                print(print(f"{user_id} {username} = status: {response.status}"))
                return True
            else:
                await bot.send_message(user_id, f"`[{i}]` ❌ An error occured = status: {response.status}", parse_mode="Markdown")
                print(print(f"{user_id} {username} = status: {response.status}"))
                return False
                

async def process_user(session, username, user_id):
    
    headers_info = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en,en-GB;q=0.9",
        "app": "WEB_MARKETPLACE",
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImJ0cy1rZXktaWQifQ.eyJhdWQiOlsib2F1dGgyLXJlc291cmNlIl0sInVzZXJfbmFtZSI6Ik1SNzU5MTA4MiIsInNjb3BlIjpbInJlYWQiLCJ3cml0ZSIsInRydXN0Il0sImV4cCI6MTc0MjQzODg4NCwiYXV0aG9yaXRpZXMiOlsiUk9MRV9VU0VSIl0sImp0aSI6Il9OYlRqRTlzMkh5Nkc5dm5ST0xHaVNVakZjOCIsImNsaWVudF9pZCI6IjU2MTU2NTYxMjcuYmVhdHN0YXJzLmNvbSJ9.GR4ev-GmCMQV8voxlcYjxsim8iwa5mWo0Nwk_pKXiXW9IbR6NfvY5TA6hfg_vqUerS1FiVwn372AZ21fD44cxLCDM8duSoX5_pt1Ju0wcu3a5HmlUx8JynHyUXfxWwJ_8TZ_XzTPfjAsAeryGlKxArEAAUGAYZA7vZx4hqdXUmpnveLlqTTF6zMlvpu0f19-lbKk2PmtTzDu0ul7T7hYTHPLVwhiV8Z4wg470ODmj75msguUY6Zw7x_nkeW4xO_ubNuvqVv8fjQGyz_Nu30eQKYU1jCigvl30639jMLowu4Qoi4nAA8KDhXoLNSfH1e-uvOzyWZGOtHLDc74XUk1IA",
        "content-type": "application/json",
        "origin": "https://www.beatstars.com",
        "priority": "u=1, i",
        "referer": "https://www.beatstars.com/",
        "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "uuid": "ba06d426-01f1-408f-a439-3b1415801cb1",
        "version": "3.14.0"
    }   

    async with lock:
        if username in checked_seller_ids:
            return None
        else:
            checked_seller_ids.add(username)
            await save_seller_id(username)
            
            url_info = f"https://main.v2.beatstars.com/musician?permalink={username}&fields=profile,user_contents,stats"
            async with session.get(url_info, headers=headers_info) as response:
                print(f"{user_id} = [FETCH INFO] = {username} = status: {response.status}")
                response_data = await response.json()
                data = response_data.get("response", {}).get("data", {})
                userid = data.get("profile").get("user_id")
                stats = data.get("stats", {})
                followers = stats.get("followers")
                tracks = stats.get("followers")
                if followers < 50 and tracks < 50:
                    return username, followers, tracks, userid
                else:
                    return None



async def main():
    global database
    database = await aiosqlite.connect('db.db')

    await load_checked_seller_ids()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())