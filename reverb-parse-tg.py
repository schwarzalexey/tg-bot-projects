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
from aiohttp import TCPConnector
import certifi
import ssl
user_stop_events = {}
lock = asyncio.Lock()  

from collections import deque


user_queue = deque()

queue_processing_task = None

BOT_TOKEN = ""
ADMIN_CHAT = ''

whitelist = []


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en",
    
    "content-type": "application/json",
    "origin": "https://reverb.com",
    "referer": "https://reverb.com/",
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0",
    "x-context-id": "f8bde3fc-2966-4e64-a282-9b17babc6221",
    "x-display-currency": "USD",
    "x-experiments": "proximity_features",
    "x-request-id": "90a2e20cefe85439d",
    "x-reverb-app": "REVERB",
    "x-reverb-device-info": '{"platform":"web","app_version":0,"platform_version":null}',
    "x-reverb-user-info": '{"mpid":null,"session_id":null,"device_id":null,"user_id":null,"ra":false,"is_bot":false}',
    "x-secondary-user-enabled": "false",
    "x-session-id": "7b3d378d-a2ec-4865-9b58-8d94e2ecebc3",
    "x-shipping-region": "XX",
    'accept-version': '3.0'
}

payload = {
    "operationName": "Core_Marketplace_CombinedMarketplaceSearch",
    "query": "query Core_Marketplace_CombinedMarketplaceSearch($inputListings: Input_reverb_search_ListingsSearchRequest, $inputBumped: Input_reverb_search_ListingsSearchRequest, $inputAggs: Input_reverb_search_ListingsSearchRequest, $shouldntLoadBumps: Boolean!, $shouldntLoadSuggestions: Boolean!, $usingListView: Boolean!, $signalGroups: [reverb_signals_Signal_Group], $useSignalSystem: Boolean!) {\n  bumpedSearch: listingsSearch(input: $inputBumped) @skip(if: $shouldntLoadBumps) {\n    listings {\n      _id\n      ...ListingCardFields\n      ...WatchBadgeData\n      ...BumpKey\n      ...ShopFields\n      ...ListViewListings @include(if: $usingListView)\n      signals(input: {groups: $signalGroups}) @include(if: $useSignalSystem) {\n        ...ListingCardSignalsData\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  aggsSearch: listingsSearch(input: $inputAggs) {\n    filters {\n      ...NestedFilter\n      __typename\n    }\n    __typename\n  }\n  listingsSearch(input: $inputListings) {\n    total\n    offset\n    limit\n    suggestedQueries\n    eligibleAutodirects\n    listings {\n      _id\n      esScore\n      ...ListingCardFields\n      ...WatchBadgeData\n      ...InOtherCartsCardData @skip(if: $useSignalSystem)\n      ...ShopFields\n      ...ListViewListings @include(if: $usingListView)\n      signals(input: {groups: $signalGroups}) @include(if: $useSignalSystem) {\n        ...ListingCardSignalsData\n        __typename\n      }\n      __typename\n    }\n    fallbackListings {\n      _id\n      ...ListingCardFields\n      ...InOtherCartsCardData @skip(if: $useSignalSystem)\n      ...WatchBadgeData\n      signals(input: {groups: $signalGroups}) @include(if: $useSignalSystem) {\n        ...ListingCardSignalsData\n        __typename\n      }\n      __typename\n    }\n    suggestions @skip(if: $shouldntLoadSuggestions) {\n      ...MarketplaceSuggestions\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment ListingCardFields on Listing {\n  _id\n  ...ListingForBuyerFields\n  ...WatchBadgeData\n  ...ListingCreateOfferButtonData\n  __typename\n}\n\nfragment ListingForBuyerFields on Listing {\n  _id\n  id\n  title\n  slug\n  listingType\n  make\n  model\n  upc\n  state\n  stateDescription\n  bumped\n  watching\n  soldAsIs\n  usOutlet\n  publishedAt {\n    seconds\n    __typename\n  }\n  condition {\n    displayName\n    conditionSlug\n    conditionUuid\n    __typename\n  }\n  pricing {\n    buyerPrice {\n      display\n      currency\n      amount\n      amountCents\n      __typename\n    }\n    originalPrice {\n      display\n      __typename\n    }\n    ribbon {\n      display\n      reason\n      __typename\n    }\n    typicalNewPriceDisplay {\n      amountDisplay\n      descriptionDisplay\n      savingsDisplay\n      __typename\n    }\n    originalPriceDescription\n    __typename\n  }\n  images(\n    input: {transform: \"card_square\", count: 3, scope: \"photos\", type: \"Product\"}\n  ) {\n    source\n    __typename\n  }\n  shipping {\n    shippingPrices {\n      _id\n      shippingMethod\n      carrierCalculated\n      destinationPostalCodeNeeded\n      rate {\n        amount\n        amountCents\n        currency\n        display\n        __typename\n      }\n      __typename\n    }\n    freeExpeditedShipping\n    localPickupOnly\n    localPickup\n    __typename\n  }\n  shop {\n    _id\n    name\n    returnPolicy {\n      usedReturnWindowDays\n      newReturnWindowDays\n      __typename\n    }\n    address {\n      _id\n      locality\n      region\n      country {\n        _id\n        countryCode\n        name\n        __typename\n      }\n      displayLocation\n      __typename\n    }\n    __typename\n  }\n  ...ListingForBuyerShippingFields\n  ...ListingGreatValueData\n  ...ListingCardCPOData\n  __typename\n}\n\nfragment ListingGreatValueData on Listing {\n  _id\n  pricing {\n    buyerPrice {\n      currency\n      amountCents\n      __typename\n    }\n    __typename\n  }\n  condition {\n    conditionSlug\n    __typename\n  }\n  priceRecommendation {\n    priceMiddle {\n      amountCents\n      currency\n      __typename\n    }\n    __typename\n  }\n  shop {\n    _id\n    address {\n      _id\n      country {\n        _id\n        countryCode\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  currency\n  __typename\n}\n\nfragment ListingForBuyerShippingFields on Listing {\n  _id\n  shipping {\n    freeExpeditedShipping\n    localPickupOnly\n    shippingPrices {\n      _id\n      shippingMethod\n      carrierCalculated\n      regional\n      destinationPostalCodeNeeded\n      postalCode\n      rate {\n        amount\n        amountCents\n        currency\n        display\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment ListingCardCPOData on Listing {\n  _id\n  id\n  certifiedPreOwned {\n    title\n    badgeIconUrl\n    __typename\n  }\n  __typename\n}\n\nfragment ListingCreateOfferButtonData on Listing {\n  id\n  _id\n  state\n  listingType\n  sellerId\n  isBuyerOfferEligible\n  ...mParticleListingFields\n  __typename\n}\n\nfragment mParticleListingFields on Listing {\n  id\n  _id\n  title\n  brandSlug\n  categoryRootUuid\n  make\n  categoryUuids\n  state\n  listingType\n  bumpEligible\n  shopId\n  inventory\n  soldAsIs\n  acceptedPaymentMethods\n  currency\n  usOutlet\n  condition {\n    conditionUuid\n    conditionSlug\n    __typename\n  }\n  categories {\n    _id\n    slug\n    rootSlug\n    __typename\n  }\n  csp {\n    _id\n    id\n    slug\n    brand {\n      _id\n      slug\n      __typename\n    }\n    __typename\n  }\n  pricing {\n    buyerPrice {\n      amount\n      currency\n      amountCents\n      __typename\n    }\n    __typename\n  }\n  publishedAt {\n    seconds\n    __typename\n  }\n  sale {\n    _id\n    id\n    code\n    buyerIneligibilityReason\n    __typename\n  }\n  shipping {\n    shippingPrices {\n      _id\n      shippingMethod\n      carrierCalculated\n      destinationPostalCodeNeeded\n      rate {\n        amount\n        amountCents\n        currency\n        display\n        __typename\n      }\n      __typename\n    }\n    freeExpeditedShipping\n    localPickupOnly\n    localPickup\n    __typename\n  }\n  certifiedPreOwned {\n    title\n    badgeIconUrl\n    __typename\n  }\n  shop {\n    _id\n    address {\n      _id\n      countryCode\n      __typename\n    }\n    returnPolicy {\n      _id\n      newReturnWindowDays\n      usedReturnWindowDays\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment WatchBadgeData on Listing {\n  _id\n  id\n  title\n  sellerId\n  watching\n  watchThumbnails: images(\n    input: {type: \"Product\", scope: \"photos\", transform: \"card_square\", count: 1}\n  ) {\n    _id\n    source\n    __typename\n  }\n  __typename\n}\n\nfragment BumpKey on Listing {\n  _id\n  bumpKey {\n    key\n    __typename\n  }\n  __typename\n}\n\nfragment ShopFields on Listing {\n  _id\n  shop {\n    _id\n    address {\n      _id\n      locality\n      countryCode\n      region\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment InOtherCartsCardData on Listing {\n  _id\n  id\n  otherBuyersWithListingInCartCounts\n  __typename\n}\n\nfragment NestedFilter on reverb_search_Filter {\n  name\n  key\n  aggregationName\n  widgetType\n  options {\n    count {\n      value\n      __typename\n    }\n    name\n    selected\n    autoselected\n    paramName\n    setValues\n    unsetValues\n    all\n    optionValue\n    trackingValue\n    subFilter {\n      widgetType\n      options {\n        count {\n          value\n          __typename\n        }\n        name\n        selected\n        autoselected\n        paramName\n        setValues\n        unsetValues\n        all\n        optionValue\n        trackingValue\n        subFilter {\n          widgetType\n          options {\n            count {\n              value\n              __typename\n            }\n            name\n            selected\n            autoselected\n            paramName\n            setValues\n            unsetValues\n            all\n            optionValue\n            trackingValue\n            subFilter {\n              widgetType\n              options {\n                count {\n                  value\n                  __typename\n                }\n                name\n                selected\n                autoselected\n                paramName\n                setValues\n                unsetValues\n                all\n                optionValue\n                trackingValue\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment MarketplaceSuggestions on reverb_search_SearchResponse_Suggestion {\n  text\n  __typename\n}\n\nfragment ListViewListings on Listing {\n  _id\n  id\n  categoryUuids\n  state\n  shop {\n    _id\n    name\n    slug\n    preferredSeller\n    quickShipper\n    quickResponder\n    address {\n      _id\n      locality\n      region\n      displayLocation\n      country {\n        _id\n        countryCode\n        name\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  seller {\n    _id\n    feedbackSummary {\n      receivedCount\n      rollingRatingPercentage\n      __typename\n    }\n    __typename\n  }\n  csp {\n    _id\n    webLink {\n      href\n      __typename\n    }\n    __typename\n  }\n  ...AddToCartButtonFields\n  ...ListingCardFields\n  ...ListingCreateOfferButtonData\n  ...InOtherCartsCardData\n  __typename\n}\n\nfragment AddToCartButtonFields on Listing {\n  _id\n  id\n  sellerId\n  listingType\n  pricing {\n    buyerPrice {\n      amount\n      amountCents\n      __typename\n    }\n    __typename\n  }\n  preorderInfo {\n    onPreorder\n    estimatedShipDate {\n      seconds\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment ListingCardSignalsData on reverb_signals_Signal {\n  name\n  title\n  icon\n  __typename\n}",
    "variables": {
        "inputAggs": {
            "query": "",
            "sortSlug": "published_at|desc",
            "categorySlugs": [],
            "brandSlugs": [],
            "conditionSlugs": [],
            "shippingRegionCodes": [],
            "itemState": [],
            "itemCity": [],
            "curatedSetSlugs": [],
            "saleSlugs": [],
            "withProximityFilter": {"proximity": False},
            "boostedItemRegionCode": "",
            "useExperimentalRecall": True,
            "traitValues": [],
            "excludeCategoryUuids": [],
            "excludeBrandSlugs": [],
            "likelihoodToSellExperimentGroup": 0,
            "countryOfOrigin": [],
            "contexts": [],
            "autodirects": "IMPROVED_DATA",
            "multiClientExperiments": [
                {"name": "ltr_v4_marketplace_2024_07", "group": "0"},
                {"name": "ltr_v5_marketplace_2024_09", "group": "0"},
                {"name": "personalized_search_v1_marketplace_2024_10", "group": "0"},
                {"name": "rerank_bump", "group": "0"}
            ],
            "canonicalFinishes": [],
            "limit": 0,
            "withAggregations": [
                "CATEGORY_SLUGS",
                "BRAND_SLUGS",
                "CONDITION_SLUGS",
                "DECADES",
                "CURATED_SETS",
                "COUNTRY_OF_ORIGIN"
            ],
            "fallbackToOr": True
        },
        "inputListings": {
            "query": "",
            "sortSlug": "published_at|desc",
            "categorySlugs": [],
            "brandSlugs": [],
            "conditionSlugs": [],
            "shippingRegionCodes": [],
            "itemState": [],
            "itemCity": [],
            "curatedSetSlugs": [],
            "saleSlugs": [],
            "withProximityFilter": {"proximity": False},
            "boostedItemRegionCode": "",
            "useExperimentalRecall": True,
            "traitValues": [],
            "excludeCategoryUuids": [],
            "excludeBrandSlugs": [],
            "likelihoodToSellExperimentGroup": 0,
            "countryOfOrigin": [],
            "contexts": [],
            "autodirects": "IMPROVED_DATA",
            "multiClientExperiments": [
                {"name": "ltr_v4_marketplace_2024_07", "group": "0"},
                {"name": "ltr_v5_marketplace_2024_09", "group": "0"},
                {"name": "personalized_search_v1_marketplace_2024_10", "group": "0"},
                {"name": "rerank_bump", "group": "0"}
            ],
            "canonicalFinishes": [],
            "limit": 500,
            "offset": 0,
            "sort": "NONE"
        },
        "shouldntLoadBumps": False,
        "shouldntLoadSuggestions": False,
        "usingListView": False,
        "signalGroups": ["MP_GRID_CARD"],
        "useSignalSystem": False
    }
}

async def process_listing(listing, session, bot, userid, headers):
    try:
        link_shit = f"{listing.get('id')}-{listing.get('slug')}"
        link = f"https://reverb.com/item/{link_shit}"

        title = listing.get("title")
        price = f"{listing.get('pricing', {}).get('buyerPrice', {}).get('amount', '0')} $"
        seller_id = str(listing.get("sellerId"))
        shop_id = listing.get("shopId")
        countryCode = listing.get("shop").get('address').get('countryCode')
        image = listing.get('images')[0].get('source')


        async with lock:
            if seller_id in checked_seller_ids:
                return None
            else:
                checked_seller_ids.add(seller_id)
                await save_seller_id(seller_id)

        async with session.get(
            f'https://api.reverb.com/api/shops/{shop_id}/feedback_summary',
            headers=headers
        ) as response2:
            if response2.status == 200:
                data2 = await response2.json()
                reviews = data2.get('total_counts').get('seller')
            else:
                await bot.send_message(userid, f"❌ Error: {response2.status}, {await response2.text()}")
                return None
        print(reviews, countryCode)
        if reviews > 2:
            return None
        await bot.send_message(
            userid,
            f"""✅ ***NEW LISTING FOUND***\n
Link: ```{link}```
Reviews: `{reviews}`
Country: `{countryCode}`
""",
            parse_mode="Markdown"
        )
        return 1

    except Exception as e:
        await bot.send_message(userid, f"An error occurred while processing a listing: {e}")
        return None


async def fetch_data(userid):
    url = "https://gql.reverb.com/graphql"
    if userid not in user_stop_events:
        user_stop_events[userid] = asyncio.Event()
    else:
        user_stop_events[userid].clear()
    found_count = 0
    stop = False
    while True:
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with aiohttp.ClientSession(connector=TCPConnector(ssl=ssl_context)) as session:
                async with session.post(url, headers=headers, data=json.dumps(payload)) as response:
                    if response.status == 200:
                        data = await response.json()
                        listings = data.get("data", {}).get("listingsSearch", {}).get("listings", [])
                        for listing in listings:
                            if user_stop_events[userid].is_set():
                                break
                            result = await process_listing(listing, session, bot, userid, headers)
                            if result is not None:
                                found_count += result

                    else:
                        await bot.send_message(userid, f"❌ Error: {response.status}, {await response.text()}")
        except Exception as e:
            await bot.send_message(userid, f"An error occurred: {e}")

        return found_count

async def process_queue():
    global queue_processing_task
    tmp = 0
    maximum = 5
    while True:
        if not user_queue:
            queue_processing_task = None
            break
        current_user = user_queue[0]
        print(user_queue)
        if current_user in user_stop_events and user_stop_events[current_user].is_set():
            user_queue.popleft()
            tmp = 0
            continue

        count = await fetch_data(current_user)
        if tmp != None:
            tmp += count

        if current_user == 0:
            maximum = 15
        else:
            maximum = 5

        if tmp >= maximum and len(user_queue) > 1:
                try:
                    print('swap')
                    user_queue.rotate(-1)
                    tmp = 0 
                    await bot.send_message(user_queue[0], f"🏳️ Your turn\nQueue lenght: `{len(user_queue)}`", parse_mode="Markdown")
                    await bot.send_message(current_user, f"🏳️ Next user `{user_queue[0]}`", parse_mode="Markdown")
                    await bot.send_message(ADMIN_CHAT, f"🏳️ Next user `{user_queue[0]}`", parse_mode="Markdown")
                    continue
                except Exception as e:
                    print(e)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in whitelist:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Start", callback_data="start_fetching")
        await message.answer("🌎 REVERB.com", reply_markup=keyboard.as_markup())


@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in whitelist:
        if user_id not in user_stop_events:
            user_stop_events[user_id] = asyncio.Event()

        user_stop_events[user_id].set()
        await bot.send_message(ADMIN_CHAT, f"`{message.from_user.username}` left the queue! 😒 ", parse_mode="Markdown")
        await message.answer('🗿 Stopped')

@dp.message(Command("queue"))
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in whitelist:
        if len(list(user_queue)) > 0:
            await message.answer(f"Queue: `{list(user_queue)}`", parse_mode="Markdown")
        else: 
            await message.answer(f"No one parsing right now 😔", parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "start_fetching")
async def start_fetching(callback_query: types.CallbackQuery):
    global queue_processing_task
    user_id = callback_query.from_user.id
    
    if user_id in whitelist:
        if user_id not in user_queue:
            if user_id in user_stop_events and user_stop_events[user_id].is_set():
                user_stop_events[user_id].clear()
            user_queue.append(user_id)
            
        await callback_query.message.edit_text(f"🚀🚀🚀\nQueue: `{list(user_queue)}`", parse_mode="Markdown")

        await bot.send_message(ADMIN_CHAT, f"`{callback_query.from_user.username}` joined the queue! 🎉 ", parse_mode="Markdown")

        
        if queue_processing_task is None:
            queue_processing_task = asyncio.create_task(process_queue())


async def main():
    await load_checked_seller_ids()
    await dp.start_polling(bot)
    await bot.send_message(ADMIN_CHAT, f"`joined the queue! 🎉 ", parse_mode="Markdown")

if __name__ == "__main__":
    asyncio.run(main())
