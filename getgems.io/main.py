import aiohttp
import asyncio
from datetime import datetime
from fake_useragent import UserAgent

async def fetch(start, end, count, balance, delay):
    f = open('filter.txt', 'r')
    shi = set(map(str.strip, f.readlines()))
    f.close()

    f = open('config.txt', 'r')
    token = f.readline().strip().split('=')[1]
    uid = int(f.readline().strip().split('=')[1])
    f.close()

    ft = open('filter.txt', 'a')
    for ts in (start, end + 1, 86400):
        excessCount = count
        isFirst = True
        while excessCount > 0:
            currCount = excessCount if excessCount < 50 else 50
            excessCount = 0 if excessCount < 50 else excessCount - 50
            if isFirst:
                isFirst = False
                url = f'https://api.getgems.io/graphql?operationName=historyCollectionNftItems&variables=%7B%22collectionAddress%22%3A%22EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi%22%2C%22count%22%3A{currCount}%2C%22types%22%3A%5B%22Mint%22%5D%2C%22minTime%22%3A{ts}%2C%22maxTime%22%3A{ts + 86400}%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%223c3c6c0b149cb83bd142b19428b7cb20a7c257256b4634e9b1155d2fbdc7177c%22%7D%7D'
            else:
                url = f'https://api.getgems.io/graphql?operationName=historyCollectionNftItems&variables=%7B%22collectionAddress%22%3A%22EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi%22%2C%22cursor%22%3A%22{prevCursor}%22%2C%22count%22%3A{currCount}%2C%22types%22%3A%5B%22Mint%22%5D%2C%22minTime%22%3A{ts}%2C%22maxTime%22%3A{ts + 86400}%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%223c3c6c0b149cb83bd142b19428b7cb20a7c257256b4634e9b1155d2fbdc7177c%22%7D%7D'
            
            headers = {
                'User-Agent': UserAgent().random,
                'Accept': 'application/json', 
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    nfts_json = await response.json()
                    await asyncio.sleep(delay)
                    if response.status != 200:
                        print(f'[✗] Something went wrong. Status code of the "nfts_json" request is {response.status}. Please, contact @ggparserfeedback_robot with a screenshot to resolve the issue.')
            try:
                nfts = nfts_json['data']['historyCollectionNftItems']['items']
            except Exception as e:
                print(nfts_json, url)
            prevCursor = nfts_json['data']['historyCollectionNftItems']['cursor'].replace(':', '%3A').replace(',', '%2C')
            for nft in nfts:
                print(f'[#] Parsing NFT {nft['nft']['name']}...')
                url = f'https://api.getgems.io/graphql?operationName=getNftByAddress&variables=%7B%22address%22%3A%22{nft['nft']['address']}%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22fb3e2f8d8cfc1f8eb59cf1663e45e47f13156f6fc8174251f9427a5633af9cfb%22%7D%7D'
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(url) as response:
                        nft_json = await response.json()
                        await asyncio.sleep(delay)
                        if response.status != 200:
                            print(f'[✗] Something went wrong. Status code of the "nft_json" request is {response.status}. Please, contact @ggparserfeedback_robot with a screenshot to resolve the issue.')

                addr = nft_json['data']['nft']['ownerAddress']

                if addr in shi:
                    print('[#] User already in filter. Skipping')
                    continue
                print(f'[#] Parsing {nft['nft']['name']} owner (TONchain address is {addr[:4]}...{addr[-4:]})...')
                shi.add(addr)
                ft.write(addr+'\n')
                userURL = f'https://api.getgems.io/graphql?operationName=getUserById&variables=%7B%22id%22%3A%22{addr}%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%222907756c1f6d5caea6516b4b588f32778d1c270206cb59321de1302af5d67e48%22%7D%7D'
                nftsURL = f'https://api.getgems.io/graphql?operationName=nftSearch&variables=%7B%22query%22%3A%22%7B%5C%22%24and%5C%22%3A%5B%7B%5C%22actualOwnerAddress%5C%22%3A%5C%22{addr}%5C%22%7D%2C%7B%5C%22isBlocked%5C%22%3Afalse%7D%2C%7B%5C%22isHiddenByUser%5C%22%3Afalse%7D%2C%7B%5C%22collectionAddressList%5C%22%3A%5B%5C%22EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi%5C%22%5D%7D%5D%7D%22%2C%22sort%22%3A%22%5B%7B%5C%22lastChangeOwnerAt%5C%22%3A%7B%5C%22order%5C%22%3A%5C%22desc%5C%22%7D%7D%5D%22%2C%22count%22%3A100%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%2288856f557ee2317541d873df84f0be35b6bddde7a6461e61a83b3530a2e5cfaa%22%7D%7D'
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(nftsURL) as response:
                        ownerNfts = await response.json()
                        await asyncio.sleep(delay)
                        if response.status != 200:
                            print(f'[✗] Something went wrong. Status code of the "ownerNfts" request is {response.status}. Please, contact @ggparserfeedback_robot with a screenshot to resolve the issue.')

                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(userURL) as response:
                        userData = await response.json()
                        await asyncio.sleep(delay)
                        if response.status != 200:
                            print(f'[✗] Something went wrong. Status code of the "userData" request is {response.status}. Please, contact @ggparserfeedback_robot with a screenshot to resolve the issue.')

                try:
                    if userData['data']['userStats'] is None:
                        bal = 0
                    else:
                        bal = float(userData['data']['userStats']['balance']) * 0.000000001

                    if ownerNfts['data']['alphaNftItemSearch']['edges']:
                        tags = [i['node']['name'] for i in ownerNfts['data']['alphaNftItemSearch']['edges']]
                        if nft['nft']['name'] not in tags:
                            tags += [nft['nft']['name']]
                    else:
                        tags = [nft['nft']['name']]
                    tags = ', '.join(tags[:50]) + '... (more tags by tonviewer.com)' if len(tags) > 50 else ', '.join(tags)

                    if bal >= balance:
                        print('[!] Found a correct user! Sending to Telegram bot...')
                        s = f'''Found a new one!\nAddress: {addr}\nBalance: ~ {round(bal, 2)} TON\nPossible usernames: {tags}'''
                        async with aiohttp.ClientSession() as session:
                            request = await session.post(f'https://api.telegram.org/bot{token}/sendMessage', data={
                                'chat_id': uid,
                                'text': s
                            })
                        if request.status == 200:
                            print('[✓] Successfully sent to your Telegram bot!')
                        else:
                            print(f'[✗] Something went wrong. Status code of the request is {request.status}. Please, contact @ggparserfeedback_robot with a screenshot to resolve the issue.')
                    else:
                        print("[✗] Users' balance is less than your minimum. Contiuning to parse...")
                except Exception as e:
                    print('[✗] Whoopsies! Exception triggered:', e, "\nPlease, contact @ggparserfeedback_robot with a screenshot to resolve the issue.")


if __name__ == '__main__':
    date = input('Start date (ex. 2022-12-31): ')
    end = input('End date (ex. 2023-01-01): ')
    count = input('How many elements for a date: ')
    balance = input('Balance in TON: ')
    delay = int(input('Delay (pref 1-2 secs): '))
    start_timestamp = int(datetime.strptime(date, '%Y-%m-%d').timestamp())
    end_timestamp = int(datetime.strptime(end, '%Y-%m-%d').timestamp())
    asyncio.run(fetch(start_timestamp,end_timestamp,int(count),float(balance),delay))
