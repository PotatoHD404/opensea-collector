import json

import aiofiles
from aiohttp import ClientSession
import asyncio
import lxml.html
from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError

COLLECTION = '0x61c0f01a77dbb995346e3e508575670ec49b5615'
NUM = 6666

path = ''


# https://opensea.io/assets/0x61c0f01a77dbb995346e3e508575670ec49b5615/6045

async def fetch(token_id, session, sem):
    async with sem:
        res = ''
        # https://hsreplay.net/api/v1/games/HUp6PycLwQ85J4keeKAhoi/?format=json
        link = f'https://opensea.io/assets/{COLLECTION}/{token_id}'
        while not res:
            try:
                async with session.get(link, timeout=10) as response:
                    print(f'Fetching token {token_id}')
                    data = await response.text()
                    html = lxml.html.fromstring(data)
                    src = html.xpath('/html/body/table[3]/tr[1]/td[3]/img')[0].attrib['src']
                    src = src.split('=')[0] + '=w16383'
                    property_names = html.xpath('//*[@id="Body react-aria-4"]/div/div/a/div/div[1]')[0].attrib['src']
                    property_values = html.xpath('//*[@id="Body react-aria-4"]/div/div/a/div/div[2]')[0].attrib['src']
                    properties = {name: {'src': src, 'value': value} for name, value in
                                  zip(property_names, property_values)}
            except (ClientOSError, ServerDisconnectedError, asyncio.TimeoutError, KeyError) as e:
                if type(e) == asyncio.TimeoutError:
                    print('Timeout error')
                elif type(e) == KeyError:
                    return
                else:
                    print(e)
        # 2**14
        async with session.get(src) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path + f'/img/{token_id}.png', mode='wb')
                await f.write(await resp.read())
                await f.close()
        f = await aiofiles.open(path + f'/json/{token_id}.json', mode='wb')
        await f.write(json.dumps(properties))
        await f.close()


# $x('//*[@id="Body react-aria-4"]/div/div/a/div/div[1]')[0].textContent
# $x('//*[@id="main"]/div/div/div/div[1]/div/div[1]/div[1]/article/div/div/div/div/img')[0].currentSrc
async def main():
    tasks = []
    sem = asyncio.Semaphore(200)

    # count = 0
    # create instance of Semaphore
    # Create client session that will ensure we dont open new connection
    # per each request.

    sem = asyncio.Semaphore(200)
    async with ClientSession() as session:
        for token_id in range(1, NUM + 1):
            task = asyncio.ensure_future(fetch(token_id, session, sem))
            tasks.append(task)
        await asyncio.gather(*tasks)
    print('Fetched all games')


# print(count)


if __name__ == "__main__":
    # start_time = time.time()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    # print("--- %s seconds ---" % (time.time() - start_time))

# https://hsreplay.net/api/v1/live/replay_feed/
