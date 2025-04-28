import asyncio
import aiohttp
import json
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
import re
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums.content_type import ContentType
import aiosqlite


user_stop_events = {}

API_TOKEN = '*'


bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class waiting_for_cookies(StatesGroup):
    waiting_for_cookies = State()

class waiting_for_paste(StatesGroup):
    waiting_for_paste = State()

class waiting_for_config(StatesGroup):
    waiting_for_config = State()

class ParseStates(StatesGroup):
    waiting_for_max_days = State()
    waiting_for_pages_to_parse = State()
    waiting_for_category = State()


BASE_URL = "https://www.gumtree.co.za"

CATEGORIES = {
    "All the ads": BASE_URL + "/s-all-the-ads/v1b0p{page}",
    
}

CONCURRENT_REQUESTS = 75
TOTAL_PAGES = 50
CHECKED_USERS_FILE = 'checked_users.txt'


years_pattern = re.compile(r'(\d+)\+?\s*years?')
months_pattern = re.compile(r'(\d+)\+?\s*months?')
days_pattern = re.compile(r'(\d+)\+?\s*days?')


COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}


last_send_time = 0
send_message_lock = asyncio.Lock()




def convert_duration_to_days(duration_str):
    years = 0
    months = 0
    days = 0

    duration_str = re.sub(r'selling for', '', duration_str.lower()).strip()

    years_match = years_pattern.search(duration_str)
    months_match = months_pattern.search(duration_str)
    days_match = days_pattern.search(duration_str)

    if years_match:
        years = int(years_match.group(1))
    if months_match:
        months = int(months_match.group(1))
    if days_match:
        days = int(days_match.group(1))

    total_days = years * 365 + months * 30 + days
    return total_days


async def fetch(session, url, logger, retries=3):
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, headers=COMMON_HEADERS) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    await logger(f"[❌] Не удалось получить {url}, статус: {response.status}")
        except Exception as e:
            await logger(f"[❌] Исключение при получении {url}: {e}")
        await asyncio.sleep(1)
    await logger(f"[❌] Не удалось получить {url} после {retries} попыток")
    return None


def parse_ads(html):
    soup = BeautifulSoup(html, 'lxml')  
    related_items = soup.find_all('span', class_='related-item')
    ads = []

    for item in related_items:
        a_tag = item.find('a', class_='related-ad-title')
        if a_tag:
            title = a_tag.get_text(strip=True)
            relative_link = a_tag.get('href')
            full_link = f"{BASE_URL}{relative_link}"
            ads.append((title, full_link))
    
    return ads


def parse_seller_info(html):
    soup = BeautifulSoup(html, 'lxml')
    seller_info = {}

    seller_name_tag = soup.find('div', class_='seller-name')
    seller_info['name'] = seller_name_tag.get_text(strip=True) if seller_name_tag else 'Неизвестно'

    seller_profile_tag = soup.find('a', class_='seller-link')
    seller_info['profile_url'] = seller_profile_tag.get('href') if (seller_profile_tag and seller_profile_tag.get('href')) else 'Неизвестно'

    stats_info = soup.find_all('div', class_='stats-info')
    for stat in stats_info:
        span = stat.find('span')
        if span:
            text = span.get_text(strip=True)
            if 'Selling for' in text:
                seller_info['selling_duration'] = text
            elif 'Total Ads' in text:
                number = stat.find('span', class_='number')
                seller_info['total_ads'] = number.get_text(strip=True) if number else 'Неизвестно'
            elif 'Active Ads' in text:
                number = stat.find('span', class_='number')
                seller_info['active_ads'] = number.get_text(strip=True) if number else 'Неизвестно'
            elif 'Total Views' in text:
                number = stat.find('span', class_='number')
                seller_info['total_views'] = number.get_text(strip=True) if number else 'Неизвестно'

    verified_info = soup.find_all('div', class_='seller-stats')
    for v_info in verified_info:
        title = v_info.find('div', class_='title')
        if title and title.get_text(strip=True) == 'Verified information':
            verified_text = v_info.find('span', class_='verified-text')
            seller_info['verified'] = verified_text.get_text(strip=True) if verified_text else 'Неизвестно'
            break
    else:
        seller_info['verified'] = 'Неизвестно'

    seller_badge = soup.find('div', class_='respond-level')
    seller_info['is_professional'] = True if (seller_badge and 'Professional Seller' in seller_badge.get_text(strip=True)) else False

    if 'selling_duration' in seller_info:
        seller_info['selling_duration_days'] = convert_duration_to_days(seller_info['selling_duration'])
    else:
        seller_info['selling_duration_days'] = 'Неизвестно'

    seller_profile_div = soup.find('div', class_='my-avatar-img')
    if seller_profile_div and 'style' in seller_profile_div.attrs:
        style_attr = seller_profile_div['style']
        match = re.search(r'background-image:\s*url\((.*?)\)', style_attr)
        if match:
            image_url = match.group(1).strip('\'"')
            seller_info['image_url'] = image_url
        else:
            seller_info['image_url'] = 'https://yt3.googleusercontent.com/YgnPXPm-UDkQKdTsrhXlWjMKsSQw2wd_EXO66FTd964kPAN77C2Cd2V6yb27cFhpzdQtx30dKQ=s900-c-k-c0x00ffffff-no-rj'
    else:
        seller_info['image_url'] = 'https://yt3.googleusercontent.com/YgnPXPm-UDkQKdTsrhXlWjMKsSQw2wd_EXO66FTd964kPAN77C2Cd2V6yb27cFhpzdQtx30dKQ=s900-c-k-c0x00ffffff-no-rj'

    return seller_info


async def fetch_seller_info(session, ad_link, semaphore, logger):
    async with semaphore:
        html = await fetch(session, ad_link, logger)
        if html:
            
            seller_info = await asyncio.to_thread(parse_seller_info, html)
            return seller_info
        else:
            return {
                'name': 'Неизвестно',
                'selling_duration_days': 'Неизвестно',
                'total_ads': 'Неизвестно',
                'active_ads': 'Неизвестно',
                'total_views': 'Неизвестно',
                'verified': 'Неизвестно',
                'is_professional': False,
                'profile_url': 'Неизвестно',
                'image_url': 'https://yt3.googleusercontent.com/YgnPXPm-UDkQKdTsrhXlWjMKsSQw2wd_EXO66FTd964kPAN77C2Cd2V6yb27cFhpzdQtx30dKQ=s900-c-k-c0x00ffffff-no-rj'
            }


async def process_ad(session, ad, semaphore, checked_users, file_handle, max_days, logger, userdata):
    title, link = ad
    seller_info = await fetch_seller_info(session, link, semaphore, logger)

    seller_id = seller_info.get('profile_url')
    if seller_id in checked_users:
        return
    else:
        checked_users.add(seller_id)
        file_handle.write(f"{seller_id}\n")
        file_handle.flush()

    selling_duration_days = seller_info.get('selling_duration_days', 'Неизвестно')
    is_professional = seller_info.get('is_professional', False)

    if not is_professional:
        if isinstance(selling_duration_days, int) and selling_duration_days < max_days:
            replaced_link = str(link).replace("https://www.gumtree.co.za", "", 1)
            name = seller_info.get('name')
            pic = seller_info.get('image_url')

            await send_message(link=replaced_link, name=name, photo=pic, logger=logger, userdata=userdata)


async def parse_single_page(session, category_name, base_category_link, page, semaphore, max_days, checked_users, file_handle, logger, userdata):
    category_link = base_category_link.format(page=page)
    
   
    html = await fetch(session, category_link, logger)
    if not html:
        return
    
    
    ads = await asyncio.to_thread(parse_ads, html)

    if not ads:
       
        return
    
    tasks = []
    for ad in ads:
        task = asyncio.create_task(process_ad(session, ad, semaphore, checked_users, file_handle, max_days, logger, userdata))
        tasks.append(task)
    await asyncio.gather(*tasks)

async def parse_category(session, category_name, base_category_link, semaphore, max_days, pages_to_parse, checked_users, file_handle, send_session, logger, userdata):
    stop_event = user_stop_events.get(userdata[0])
    
    while True:
        if stop_event.is_set():
            break
        pages = range(1, pages_to_parse + 1)
        tasks = []
        await logger(f"[✔] Starting parse - {category_name} - {pages_to_parse}")
        for page in pages:
            task = asyncio.create_task(parse_single_page(session, category_name, base_category_link, page, semaphore, max_days, checked_users, file_handle, send_session, userdata))
            tasks.append(task)

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass


def get_categories_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    buttons = []
    for idx, category in enumerate(CATEGORIES.keys(), 1):
        buttons.append([InlineKeyboardButton(text=category, callback_data=f"category_{idx}")])
    keyboard.inline_keyboard = buttons
    return keyboard


def load_checked_users(file_path):
    checked = set()
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                checked.add(line.strip())
    return checked


async def send_message(link, name, photo, logger, userdata):
    global last_send_time, send_message_lock

    API_LINK_FIRST = "https://www.gumtree.co.za/api/items/reply?noredirect"
    API_LINK_SECOND = "https://www.gumtree.co.za/api/conversation?offset=1&limit="
    API_LINK_THIRD = "https://www.gumtree.co.za/api/conversation"

    async def generate_link(name, photo, uid):
        data = {
            'api_key': 'PkYCig4uQ7VFn3HJMTbMVzqSnaMHuxb2',
            'title': name, 
            'photo': photo, 
            'service': 'gumtreeVerif_za',
            'userId': uid,
        }

        async with aiohttp.ClientSession() as temp_session:
            req = await temp_session.post("", data=data)
            response = await req.json()
            lnk = str(response.get('message', ''))
            return lnk.replace('s3', 'gumtree', 1).replace('https://', '')

    async with send_message_lock:
        now = time.time()
        elapsed = now - last_send_time
        if elapsed < 30:
            await asyncio.sleep(30 - elapsed)

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-AU,en-GB;q=0.9,en;q=0.8",
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Method": "POST",
            "Origin": "https://www.gumtree.co.za",
            "Priority": "u=1, i",
            "Referer": f"https://www.gumtree.co.za{link}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "YaBrowser";v="24.10", "Yowser";v="2.5"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': "Android", 
            "Csrf-Token": userdata[4],
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            'Cookie': userdata[1]
        }
        
        connector = ProxyConnector.from_url('socks5://127.0.0.1:60000')

        status_codes = []

        async with aiohttp.ClientSession(connector=connector) as proxy_session:
            adId = link.split('/')[-1]

            lnk = await generate_link(name, photo, userdata[0])

            data_first = {
                'adId': adId,
                'buyerName': userdata[3],
                'email': userdata[5],
                'phoneNumber': '',
                'replyMessage': '---',
                'seoUrl': link
            }
            
            try: 
                send_first_message = await proxy_session.post(API_LINK_FIRST, headers=headers, data=data_first)

                if send_first_message.status != 200:
                    await logger(f'[❌] Ошибка в запросе при отправке первого сообщения: {await send_first_message.text()} {send_first_message.status}')
                    if '0 bytes' in (await send_first_message.text()):
                        print(data_first)
                    return
                
            except Exception as e:
                await logger(f'[❌] Ошибка при отправке первого сообщения: {e}')
                return
            try:
                status_codes.append(send_first_message.status)
            except Exception as e:
                await logger('bzz')
                status_codes.append('Internal error')
                return
            try:
                request_messages = await proxy_session.get(API_LINK_SECOND, headers=headers)

                if request_messages.status == 200:
                    json_response = await request_messages.json()
                    
                    message_id = json_response["conversations"][0]["id"]
                    to_id = json_response["conversations"][0]["peerInfo"]["userId"]
                    ad_title = json_response["conversations"][0]["adInfo"]["adTitle"]

                else: 
                    await logger(f'[❌] Ошибка при запросе сообщений: {await request_messages.text()}')
                    await logger(f'[❌] Статус: {request_messages.status}')
                    return
        
            except Exception as e:
                await logger(f'[❌] Исключение при запросе сообщений: {e}')
                return
            try:    
                status_codes.append(request_messages.status)
            except Exception as e:
                status_codes.append('Internal error')
                await logger('bzz')
                return
            subject = f"Gumtree - Reply to ad: {ad_title} - 

            data_second = {
                'adId': adId,
                'content': userdata[2].replace('{NAME}', name).replace('{LINK}', lnk),
                'conversationId': message_id,
                'role': "BUYER",
                'subject': subject,
                'to': to_id,
            }
            try: 
                send_second_message = await proxy_session.post(API_LINK_THIRD, headers=headers, data=data_second)
                try:
                    status_codes.append(send_second_message.status)
                except Exception as e:
                    status_codes.append('Internal error')
                    await logger('bzz')
                    return
                if send_second_message.status != 200: 
                    await logger(f'[❌] Ошибка при отправке второго сообщения: {await send_second_message.text()}')
                    return
                
            except Exception as e:
                await logger(f'[❌] Исключение при отправке второго сообщения: {e}')
                return
            
            await logger(f'{"✅ Sent" if all(code == 200 for code in status_codes) else "⛔️ Failed to send"} message to {name} (`{link}`): [{status_codes}]')

            try: 
                send_check_message = await proxy_session.get('https://www.gumtree.co.za/my/message.html', headers=headers)

                try:
                    status_codes.append(send_check_message.status)
                except Exception as e:
                    status_codes.append('Internal error')
                    await logger('bzz')
                    return
                if send_check_message.status != 200: 
                    await logger(f'[❌] Ошибка при отправке сообщения на проверку: {await send_check_message.text()}')
                    return
                elif (await send_check_message.text()) == '':
                    await logger(f'[❌] Ваш аккаунт на гамтри заблокирован; проверьте пасту')
            except Exception as e:
                await logger(f'[❌] Исключение при отправке сообщения на проверку: {e}')
                return
            last_send_time = time.time()
       


async def start_parse(max_days, pages_to_parse, category_name, logger, userdata):
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    checked_users = load_checked_users(CHECKED_USERS_FILE)
    await logger(f"✅ Загружено {len(checked_users)} проверенных пользователей.\n")

    async with aiohttp.ClientSession() as session:
        selected_category = category_name
        base_category_link = CATEGORIES[selected_category]

        with open(CHECKED_USERS_FILE, 'a', encoding='utf-8') as file_handle:
            
            await parse_category(session, selected_category, base_category_link, semaphore, max_days, pages_to_parse, checked_users, file_handle, logger, logger, userdata)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    result = await (await database.execute('SELECT uid FROM users WHERE uid=?', (message.from_user.id,))).fetchone()
    if result is None:
        return

    result = await (await database.execute('SELECT uid FROM settings WHERE uid=?', (message.from_user.id,))).fetchone()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="запустить шарманку", callback_data="start_sender")],
        [InlineKeyboardButton(text="повторить предыдущий пресет", callback_data="restart")] if result is not None else [],
        [InlineKeyboardButton(text="заебало меня это все", callback_data="stop_sender")],
        [InlineKeyboardButton(text="настройки", callback_data="setup")],
        [InlineKeyboardButton(text='свап прокси', callback_data='proxy')]
    ])
    await message.answer("", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "proxy")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    async with aiohttp.ClientSession() as s:
        rq = await s.get('http://127.0.0.1:10101/api/proxy?num=1&country=ZA&port=60000')
    await callback.message.answer(f"прокси сменено с статус кодом {rq.status}")

@dp.callback_query(lambda c: c.data == "setup")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить куки", callback_data="setup_cookies")],
        [InlineKeyboardButton(text="Изменить пасту", callback_data="setup_paste")],
        [InlineKeyboardButton(text="Изменить конфиг", callback_data="setup_config")],
    ])    

    await callback.message.answer("🔧 настроечкби", reply_markup=keyboard)
    
    

@dp.callback_query(lambda c: c.data == "setup_cookies")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔧 Пожалуйста, загрузите файл `cookies.json`.")
    await state.set_state(waiting_for_cookies.waiting_for_cookies)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "setup_config")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔧 Пожалуйста, загрузите файл `config.txt`.")
    await state.set_state(waiting_for_config.waiting_for_config)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "setup_paste")
async def handle_setup(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔧 Пожалуйста, загрузите файл `paste.txt`.")
    await state.set_state(waiting_for_paste.waiting_for_paste)
    await callback.answer()

@dp.message(waiting_for_cookies.waiting_for_cookies)
async def process_cookies(message: types.Message, state: FSMContext):
    document = message.document
    if document.file_name != 'cookies.json':
        await message.answer("❌ Пожалуйста, загрузите файл с именем `cookies.json`.")
        return

    
    await message.bot.download(file=document, destination=f"shit/{message.from_user.id}.json")
    
    
    with open(f'shit/{message.from_user.id}.json', 'r') as f:
        cookies_data = json.loads(f.read().strip())
    
    
    if isinstance(cookies_data, list) and all('name' in cookie and 'value' in cookie for cookie in cookies_data):
        await database.execute('UPDATE users SET cookies=? WHERE uid=?', ('; '.join([f"{x['name']}={x['value']}" for x in cookies_data]),message.from_user.id))
        await database.commit()
        await message.answer("✅ Файл `cookies.json` успешно загружен.")
        await state.clear()
        
    else:
        await message.answer("❌ Структура файла `cookies.json` некорректна. Убедитесь, что это список объектов с полями `name` и `value`.")




@dp.message(waiting_for_config.waiting_for_config)
async def process_config(message: types.Message, state: FSMContext):
    document = message.document
    if document.file_name != 'config.txt':
        await message.answer("❌ Пожалуйста, загрузите файл с именем `config.txt`.")
        return
    try:
        file = await message.bot.download(file=document, destination=f"shit/{message.from_user.id}config.txt")
        with open(f'shit/{message.from_user.id}config.txt', 'r', encoding='utf-8') as f:
            config_lines = list(map(str.strip, f.readlines()))

        config_data = {}
        for line in config_lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config_data[key] = value
        await database.execute('UPDATE users SET name=?, email=?, csrf=? WHERE uid=?', (config_data['name'],config_data['email'],config_data['csrf'],message.from_user.id))
        await database.commit()
        await message.answer("✅ Файл `config.txt` успешно загружен.")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла `config.txt`: {e}")


@dp.message(waiting_for_paste.waiting_for_paste)
async def process_paste(message: types.Message, state: FSMContext):
    document = message.document
    if document.file_name != 'paste.txt':
        await message.answer("❌ Пожалуйста, загрузите файл с именем `paste.txt`.")
        return
    try:
        await message.bot.download(file=document, destination=f"shit/{message.from_user.id}paste.txt")
        with open(f'shit/{message.from_user.id}paste.txt', 'r', encoding='utf-8') as f:
            paste_content = f.read()

        await database.execute('UPDATE users SET paste=? WHERE uid=?', (paste_content, message.from_user.id))
        await database.commit()
        await message.answer("✅ Файл `paste.txt` успешно загружен.")
        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла `paste.txt`: {e}")


@dp.callback_query(lambda c: c.data == "start_sender")
async def handle_start_parse(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите максимальное количество дней стажа продаж продавца:")
    await state.set_state(ParseStates.waiting_for_max_days)
    await callback.answer()


@dp.message(ParseStates.waiting_for_max_days)
async def process_max_days(message: types.Message, state: FSMContext):
    try:
        max_days = int(message.text.strip())
        if max_days < 0:
            await message.answer("❗ Пожалуйста, введите положительное число.\nВведите максимальное количество дней стажа продаж продавца:")
            return
        await state.update_data(max_days=max_days)
        await message.answer(f"✅ Максимальное количество дней установлено на {max_days}.\nВведите количество страниц для парсинга за один цикл (максимум {TOTAL_PAGES}):")
        await state.set_state(ParseStates.waiting_for_pages_to_parse)
    except ValueError:
        await message.answer("❌ Некорректный ввод. Пожалуйста, введите целое число.\nВведите максимальное количество дней стажа продаж продавца:")


@dp.message(ParseStates.waiting_for_pages_to_parse)
async def process_pages_to_parse(message: types.Message, state: FSMContext):
    try:
        pages_to_parse = int(message.text.strip())
        if pages_to_parse <= 0:
            await message.answer("❗ Пожалуйста, введите положительное число.\nВведите количество страниц для парсинга за один цикл:")
            return
        if pages_to_parse > TOTAL_PAGES:
            pages_to_parse = TOTAL_PAGES
            await message.answer(f"⚠️ Количество страниц не может превышать {TOTAL_PAGES}. Установлено значение {TOTAL_PAGES}.")
        await state.update_data(pages_to_parse=pages_to_parse)
        categories_text = "📂 Выберите категорию для парсинга:"
        keyboard = get_categories_keyboard()
        await message.answer(categories_text, reply_markup=keyboard)
        await state.set_state(ParseStates.waiting_for_category)
    except ValueError:
        await message.answer("❌ Некорректный ввод. Пожалуйста, введите целое число.\nВведите количество страниц для парсинга за один цикл:")

@dp.callback_query(lambda c: c.data == "stop_sender")
async def stop_parsing(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    
    if user_id in user_stop_events:
        user_stop_events[user_id].set()  
        await bot.send_message(user_id, "остановил\n\nподожди, пока завершатся все задачи и запускай шарманочку заново")
    else:
        await bot.send_message(user_id, "нахуй ты это жмешь идиот")


@dp.callback_query(lambda c: c.data == 'restart')
async def restart_sender(callback):
    data = await (await database.execute('SELECT * FROM users WHERE uid=?', (callback.from_user.id,))).fetchone()
    settings = await (await database.execute('SELECT max_days, pages, category FROM settings WHERE uid=?', (callback.from_user.id,))).fetchone()

    async def logger(log_message):
        await callback.message.answer(log_message, parse_mode="Markdown")

    user_id = callback.from_user.id

    if user_id not in user_stop_events:
        user_stop_events[user_id] = asyncio.Event()
    else:
        user_stop_events[user_id].clear() 

    await callback.message.answer(f"🚀 Начинаю парсинг категории '{settings[2]}' с `max_days={settings[0]}` и `pages_to_parse={settings[1]}`", parse_mode="Markdown")

    asyncio.create_task(
            start_parse(
                max_days=settings[0],
                pages_to_parse=settings[1],
                category_name=settings[2],
                logger=logger,
                userdata=data,
            )
        )
    await callback.message.answer("🔍 Парсинг начался. Вы будете получать обновления.")


@dp.callback_query(lambda c: c.data and c.data.startswith("category_"))
async def process_category_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        choice = int(callback.data.split("_")[1])
        if choice < 1 or choice > len(CATEGORIES):
            await callback.message.answer("❌ Некорректный выбор категории. Попробуйте снова.")
            await callback.answer()
            return
        selected_category = list(CATEGORIES.keys())[choice - 1]
        user_data = await state.get_data()
        max_days = user_data['max_days']
        pages_to_parse = user_data['pages_to_parse']

        check = await (await database.execute('SELECT uid FROM settings WHERE uid=?', (callback.from_user.id,))).fetchone()
        
        if check is None:
            await database.execute('INSERT INTO settings (uid, max_days, pages, category) VALUES (?, ?, ?, ?)', (callback.from_user.id,max_days,pages_to_parse,selected_category))
            await database.commit()
        else:
            await database.execute('UPDATE settings SET max_days=?, pages=?, category=? WHERE uid=?', (max_days,pages_to_parse,selected_category,callback.from_user.id,))
            await database.commit()

        await callback.message.answer(f"🚀 Начинаю парсинг категории '{selected_category}' с `max_days={max_days}` и `pages_to_parse={pages_to_parse}`", parse_mode="Markdown")

        user_id = callback.from_user.id

        if user_id not in user_stop_events:
            user_stop_events[user_id] = asyncio.Event()
        else:
            user_stop_events[user_id].clear() 

        
        async def logger(log_message):
            await callback.message.answer(log_message, parse_mode="Markdown")

        data = await (await database.execute('SELECT * from users where uid=?', (callback.from_user.id,))).fetchone()
        
        asyncio.create_task(
            start_parse(
                max_days=max_days,
                pages_to_parse=pages_to_parse,
                category_name=selected_category,
                logger=logger,
                userdata=data,
            )
        )

        await callback.message.answer("🔍 Парсинг начался. Вы будете получать обновления.")
        await state.clear()
        await callback.answer()
    except (IndexError, ValueError):
        await callback.message.answer("❌ Некорректный выбор категории. Попробуйте снова.")
        await callback.answer()


async def main():
    global database
    database = await aiosqlite.connect('db.db')
    
    

    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
