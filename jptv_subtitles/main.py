import asyncio
import logging
import aiohttp
import lxml
import attr
import json
from bs4 import BeautifulSoup

logging.basicConfig(level="INFO")
logger = logging.getLogger("root")

def entrypoint():
    m = Main()
    asyncio.run(m.run(), debug=False)


@attr.define(frozen=True)
class SubtitleRecord:
    subtitle_category:str
    language:str
    extension:str
    size:str
    downloads:str
    uploaded:str
    uploader:str


class Main:


    def __init__(self):

        with open("cookies.json", "r", encoding="utf-8") as f:
            self.cookies = json.load(f)

        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0"}


    async def run(self):

        logger.info("creating session")
        async with aiohttp.ClientSession(cookies=self.cookies, headers=self.headers) as aiohttp_session:

            logger.info("getting initial subtitle page")
            main_subtitle_result = await aiohttp_session.get("https://jptv.club/subtitles")

            main_subtitle_page_result_text = await main_subtitle_result.text()

            logger.info("main subtitle page result: `%s`", main_subtitle_result)
            soup = BeautifulSoup(main_subtitle_page_result_text, "lxml")


            rows = soup.select("table.table > tbody > tr")

            #for iterRow in rows:
            breakpoint()
