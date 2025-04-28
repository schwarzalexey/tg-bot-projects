import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from bs4 import BeautifulSoup
import io
from io import BytesIO
import asyncio
import aiohttp
import ssl
import traceback
import tempfile
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InputFile, FSInputFile
import requests
import qrcode
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from datetime import datetime, timedelta


BOT_TOKEN = ''
ADMIN_CHAT_ID = 0
BASE_IMAGE_PATH = "10.png"
FONT_PATH_BOLD = "fontbold.ttf"
FONT_PATH_REGULAR = "fontregular.ttf"
TEXT_COLOR = "#e6e6e6"
WHITELIST = [577348184, 6093544857, 321979716, 7211953783, 5354997888, 7543191979, 8194874877]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

img = Image.open(BASE_IMAGE_PATH)
dpi = img.info.get('dpi', (72, 72))

REFERENCE_DPI = 96  
PILLOW_DPI = dpi[0] 
SCALE_FACTOR = REFERENCE_DPI / PILLOW_DPI  

COORDINATES_SCALED = [
    (int(393 * SCALE_FACTOR), int(139 * SCALE_FACTOR)),
    (int(120 * SCALE_FACTOR), int(312 * SCALE_FACTOR)),
    (int(108 * SCALE_FACTOR), int(630 * SCALE_FACTOR)),
    (int(508 * SCALE_FACTOR), int(638 * SCALE_FACTOR))
]

LETTER_SPACING_VALUES = [-0.62, -0.62, -0.62, -0.62]

async def download_image(image_path: str) -> Image.Image:
    if image_path.startswith("http://") or image_path.startswith("https://"):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(image_path) as response:
                image_data = await response.read()
        image = Image.open(BytesIO(image_data))
    else:
        image = Image.open(image_path)

    return image

def round_corners(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    
    rounded_image = ImageOps.fit(image, image.size, centering=(0.5, 0.5))
    rounded_image.putalpha(mask)
    
    return rounded_image

def create_qrcode(data: str, logo_path: str, size: int = 400, logo_size: int = 150) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=24,
        border=0,
    )

    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer(), color_mask=SolidFillColorMask(front_color=(181, 232, 65), back_color=(45, 44, 41))).convert("RGBA")
    
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((logo_size, logo_size))
    
    qr_width, qr_height = qr_img.size
    logo_position = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
    
    logo = round_corners(logo, radius=25)
    qr_img.paste(logo, logo_position, mask=logo)
    qr_img = qr_img.resize((size, size))
    qr_img = round_corners(qr_img, 50)
    return qr_img

def clamp(text, val=25):
    return text[:val] + '...' if len(text) > 25 else text[:val]

async def parse_klein_item(url: str) -> dict:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            product_title = soup.find('h1', id='viewad-title').get_text(strip=True)
            price_amount = soup.find('meta', itemprop='price')['content']
            image_url = soup.find('img', id='viewad-image')['src']
            profile_username = soup.find('span', class_='userprofile-vip').get_text(strip=True)

            return {
                "product_title": product_title,
                "price": f"{price_amount} €",
                "image_url": image_url,
                "profile_username": profile_username,
            }
        

async def improve_image(url: str, chat_id, image_path: str):
    product_info = await parse_klein_item(url)
    
    img = Image.open(image_path).convert("RGBA")
    background = await download_image(product_info["image_url"])

    overlay_width, overlay_height = img.size
    background_resized = background.resize((overlay_width, int(background.size[1] * (overlay_width / background.size[0]))))
    background_cropped = background_resized.crop((0, background_resized.size[1] // 2 - 400, overlay_width, background_resized.size[1] // 2 + 400))
    print(background_resized.size[1] // 2 - 400, background_resized.size[1] // 2 + 400, background_cropped.size)
    overlay_imaged = Image.new("RGBA", (overlay_width, overlay_height))

    overlay_imaged.paste(img, (0, 0), img)
    overlay_imaged.paste(background_cropped, (0, 0))


    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    json = {'api_key': '', 'title': product_info["product_title"], 'name': product_info["profile_username"], 'price': product_info["price"], 'userId': chat_id, 'photo': product_info["image_url"], 'address': 'Birkelweg 22, 89555, Witten, Germany', 'service': 'ebay_de'}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.post('', data=json) as kartatai_response:
            response = await kartatai_response.json()
            unique_link = response.get('message')
            

    text_lines = [
        [clamp(product_info["product_title"]), (40,900), (221, 219, 213), ImageFont.truetype(FONT_PATH_BOLD, int(54 * SCALE_FACTOR))],
        [product_info["price"], (40,985), (211, 242, 141), ImageFont.truetype(FONT_PATH_REGULAR, int(42 * SCALE_FACTOR))],
        [(datetime.now() - timedelta(hours=1)).strftime('%d.%m.%y, %H:%M'), (97, 1260), (221, 219, 213), ImageFont.truetype(FONT_PATH_REGULAR, int(28 * SCALE_FACTOR))]
    ]
    
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw_text = ImageDraw.Draw(txt_layer)
    draw_text.fontmode = "1"

    for line in text_lines:
        draw_text.text(line[1], line[0], line[2], font=line[3])

    combined = Image.alpha_composite(overlay_imaged, txt_layer)
    qr_img = create_qrcode(unique_link, 'kleinanzeigen_logo.png')
    combined.paste(qr_img, (73, 1765))

    with io.BytesIO() as output:
        combined.convert("RGB").save(output, format="PNG")
        output.seek(0)
        return output.getvalue(), product_info, unique_link


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    if message.from_user.id in WHITELIST:
        await message.answer(
            "<b>🖼 Формат введения:</b>\n\n⚠️ Ссылка на объявление Kleinanzeigen!",
            parse_mode='HTML'
        )


@dp.message()
async def handle_message(message: types.Message):
    if message.from_user.id in WHITELIST:
        try:
            text = message.text
            lines = text.splitlines()

            if len(lines) == 1:
                url = lines[0].strip()
                if url.startswith("http://") or url.startswith("https://"):
                    text_creating = await message.reply("<b>🎭 Создаю картинку</b>", parse_mode='HTML')
                    image_data, product_info, unique_link = await improve_image(url, message.chat.id,BASE_IMAGE_PATH)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                        tmp_file.write(image_data)
                        tmp_file_name = tmp_file.name 

                    photo = FSInputFile(tmp_file_name)

                    await bot.delete_message(chat_id=message.chat.id, message_id=text_creating.message_id)
                    await message.answer_photo(photo, f"<b>🛍 {product_info['product_title']}</b>\n\n<b>🦣 Продавец:</b> <code>{product_info['profile_username']}</code>\n<b>💸 Цена:</b> <code>{product_info['price']}</code>\n\n🔗 <code>{unique_link}</code>", parse_mode='HTML')

                    await bot.send_photo(ADMIN_CHAT_ID, photo, caption=f"<b>✅ Пользователь @{message.from_user.username} (ID: {message.from_user.id}) сгенерировал изображение.</b>\n\nПродавец: {product_info['profile_username']}\nЦена: {product_info['price']}\n\n<code>{unique_link}</code>", parse_mode='HTML')
                    os.unlink(tmp_file_name)
                else:
                    await message.reply("<b>🔗 Только ссылки!</b>\nПожалуйста, убедитесь, что вы отправляете только ссылки на товар.", parse_mode='HTML')
                    await bot.send_message(ADMIN_CHAT_ID, f"<b>⚡️ Дебил @{message.from_user.username} пишет чепуху вместо ссылок</b>", parse_mode='HTML')
                    await message.forward(chat_id=ADMIN_CHAT_ID)
            else:
                await message.reply("<b>❌ Неверный формат сообщения!</b>\n📌 Попробуйте снова, следуя указанному формату.", parse_mode='HTML')

        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"\n{e}\n\n{tb}"
            await bot.send_message(ADMIN_CHAT_ID, f"🚨 <b> [Ошибка] [@{message.from_user.username} | {message.from_user.id}]</b>\n\n{error_message}", parse_mode='HTML')
            await message.forward(chat_id=ADMIN_CHAT_ID)


async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        tb = traceback.format_exc()
        error_message = f"Бот упал с ошибкой:\n{e}\n\n{tb}"
        print(error_message)
        await bot.send_message(ADMIN_CHAT_ID, f"[CRASH] {error_message}")
        await asyncio.sleep(5)
        print("Restarting bot...")
        await main()


if __name__ == "__main__":
    asyncio.run(main())