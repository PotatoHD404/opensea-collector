import asyncio

import aiofiles
import requests
import os
import json
import math

from aiohttp import ClientSession, ClientOSError, ServerDisconnectedError, InvalidURL
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


async def main():
    # This is where you add the collection name to the URL
    collection_name = "wickensnft".lower()

    # Random User Agent
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    user_agent = user_agent_rotator.get_random_user_agent()

    # Headers for the request. Currently, this is generating random user agents
    # Use a custom header version here -> https://www.whatismybrowser.com/guides/the-latest-user-agent/
    headers = {
        'User-Agent': user_agent
    }

    # Get information regarding collection

    collection = requests.get(f"https://api.opensea.io/api/v1/collection/{collection_name}?format=json")

    if collection.status_code == 429:
        print("Server returned HTTP 429. Request was throttled. Please try again in about 5 minutes.")

    if collection.status_code == 404:
        print(
            "NFT Collection not found.\n\n(Hint: Try changing the name of the collection in the Python script, line 6.)")
        exit()

    collection_info = json.loads(collection.content.decode())

    # Create image folder if it doesn't exist.

    if not os.path.exists('./images'):
        os.mkdir('./images')

    if not os.path.exists(f'./images/{collection_name}'):
        os.mkdir(f'./images/{collection_name}')

    if not os.path.exists(f'./images/{collection_name}/image_data'):
        os.mkdir(f'./images/{collection_name}/image_data')

    # Get total NFT count

    count = int(collection_info["collection"]["stats"]["count"])

    # Opensea limits to 50 assets per API request, so here we do the division and round up.

    iterator = math.ceil(count / 50)

    print(f"\nBeginning download of \"{collection_name}\" collection.\n")

    # Define variables for statistics

    stats = {
        "DownloadedData": 0,
        "AlreadyDownloadedData": 0,
        "DownloadedImages": 0,
        "AlreadyDownloadedImages": 0,
        "FailedImages": 0
    }
    tasks = []
    sem = asyncio.Semaphore(50)
    async with ClientSession() as session:
        # Iterate through every unit
        for i in range(iterator):
            offset = i * 50
            data = json.loads(requests.get(
                f"https://api.opensea.io/api/v1/assets?order_direction=asc&offset={offset}&limit=50&collection={collection_name}&format=json",
                headers=headers).content.decode())

            if "assets" in data:
                for j, asset in enumerate(data["assets"]):
                    formatted_number = f"{int(asset['token_id']):04d}"

                    print(f"\n#{formatted_number}:")

                    # Check if data for the NFT already exists, if it does, skip saving it
                    if os.path.exists(f'./images/{collection_name}/image_data/{formatted_number}.json'):
                        print(f"  Data  -> [\u2713] (Already Downloaded)")
                        stats["AlreadyDownloadedData"] += 1
                    else:
                        # Take the JSON from the URL, and dump it to the respective file.
                        dfile = open(f"./images/{collection_name}/image_data/{formatted_number}.json", "w+")
                        json.dump(asset, dfile, indent=3)
                        dfile.close()
                        print(f"  Data  -> [\u2713] (Successfully downloaded)")
                        stats["DownloadedData"] += 1

                    # Check if image already exists, if it does, skip saving it
                    if os.path.exists(f'./images/{collection_name}/{formatted_number}.png'):
                        print(f"  Image -> [\u2713] (Already Downloaded)")
                        stats["AlreadyDownloadedImages"] += 1
                    else:
                        # Make the request to the URL to get the image
                        if not asset["image_original_url"] is None:
                            image = asset["image_original_url"]
                        else:
                            image = asset["image_url"]
                        if image == '':
                            print(j)
                        else:
                            task = asyncio.ensure_future(
                                fetch(image, f'./images/{collection_name}/{formatted_number}.png', session, sem))
                            tasks.append(task)
                await asyncio.gather(*tasks)
                tasks = []

    print(f"""
    
    Finished downloading collection.
    
    
    Statistics
    -=-=-=-=-=-
    
    Total of {count} units in collection "{collection_name}".
    
    Downloads:
    
      JSON Files ->
        {stats["DownloadedData"]} successfully downloaded
        {stats["AlreadyDownloadedData"]} already downloaded
    
      Images ->
        {stats["DownloadedImages"]} successfully downloaded
        {stats["AlreadyDownloadedImages"]} already downloaded
        {stats["FailedImages"]} failed
    
    
    You can find the images in the images/{collection_name} folder.
    The JSON for each NFT can be found in the images/{collection_name}/image_data folder.
    Press enter to exit...""")
    input()


async def fetch(link, path, session, sem):
    async with sem:
        res = False
        # https://hsreplay.net/api/v1/games/HUp6PycLwQ85J4keeKAhoi/?format=json
        while not res:
            try:
                async with session.get(link, timeout=10) as response:
                    if response.status == 200:
                        f = await aiofiles.open(path, mode='wb+')
                        await f.write(await response.read())
                        await f.close()
                        res = True
            except (ClientOSError, ServerDisconnectedError, asyncio.TimeoutError, KeyError, InvalidURL) as e:
                if type(e) == asyncio.TimeoutError:
                    print('Timeout error')
                elif type(e) == asyncio.TimeoutError:
                    print(link)
                elif type(e) == KeyError:
                    return
                else:
                    print(e)


if __name__ == "__main__":
    # start_time = time.time()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
