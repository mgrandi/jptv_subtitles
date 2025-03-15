import asyncio
import logging
import aiohttp
import lxml
import arrow
import pathlib
import re
import attrs
import json
from bs4 import BeautifulSoup

logging.basicConfig(level="INFO")
logger = logging.getLogger("root")

def entrypoint():
    m = Main()
    asyncio.run(m.run(), debug=False)


@attrs.define(frozen=True)
class SubtitleRecord:
    subtitle_id:int
    subtitle_category:str
    torrent_title:str
    language:str
    subtitle_download_link:str
    extension:str
    size:str
    downloads:str
    date_uploaded:str
    current_time:str
    uploader:dict


subtitle_id_regex = re.compile("https://jptv.club/subtitles/(?P<id>[0-9]+)/download")

class Main:


    def __init__(self):

        with open("cookies.json", "r", encoding="utf-8") as f:
            self.cookies = json.load(f)

        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0"}


    async def run(self):

        logger.info("creating session")
        async with aiohttp.ClientSession(cookies=self.cookies, headers=self.headers) as aiohttp_session:

            logger.info("getting initial subtitle page")


            current_page = 1
            while True:
                logger.info("on page `%s`", current_page)
                main_subtitle_result = await aiohttp_session.get(f"https://jptv.club/subtitles?page={current_page}")

                main_subtitle_page_result_text = await main_subtitle_result.text()

                logger.debug("main subtitle page result: `%s`", main_subtitle_result)
                soup = BeautifulSoup(main_subtitle_page_result_text, "lxml")
                rows = soup.select("table.table > tbody > tr")
                subtitle_records = list()


                if len(rows) == 0:

                    logger.info("0 rows returned, at the end of the subtitle pages?")
                    break
                for iter_tr_element in rows:
                    category_str = self.get_category_string(iter_tr_element)
                    logger.debug("category: `%s`", category_str)

                    title_str = self.get_title_string(iter_tr_element).strip()
                    logger.debug("title: `%s`", title_str)

                    language_str = self.get_language_string(iter_tr_element).strip()
                    logger.debug("language: `%s`", language_str)

                    download_link = self.get_download_link(iter_tr_element)
                    logger.debug("download link: `%s`", download_link)

                    extension_str = self.get_extension_string(iter_tr_element)
                    logger.debug("extension: `%s`", extension_str)

                    size_str = self.get_size_str(iter_tr_element)
                    logger.debug("size: `%s`", size_str)

                    download_count = self.get_download_count_str(iter_tr_element)
                    logger.debug("downloads: `%s`", download_count)

                    time_str = self.get_relative_download_time(iter_tr_element)
                    logger.debug("time: `%s`", time_str)

                    user_dict = self.get_user_html(iter_tr_element)
                    logger.debug("user: `%s`", user_dict)

                    subtitle_id = subtitle_id_regex.match(download_link).groupdict()["id"]
                    record = SubtitleRecord(
                        subtitle_id=subtitle_id,
                        subtitle_category=category_str,
                        torrent_title=title_str,
                        language=language_str,
                        subtitle_download_link=download_link,
                        extension=extension_str,
                        size=size_str,
                        downloads=download_count,
                        date_uploaded=time_str,
                        current_time=arrow.utcnow().isoformat(),
                        uploader=user_dict
                        )

                    subtitle_records.append(record)

                logger.debug("records: `%s`", subtitle_records)


                for iter_record in subtitle_records:

                    # download record

                    logger.info("downloading subtitle `%s` - `%s` - `%s`",
                        iter_record.subtitle_id, iter_record.language, iter_record.torrent_title )

                    subtitle_dl_result = await aiohttp_session.get(iter_record.subtitle_download_link)

                    basedir = pathlib.Path.cwd() / "subtitles"
                    basedir.mkdir(exist_ok=True)


                    safename = iter_record.torrent_title.replace("/", "_")
                    if len(safename) > 60:
                        safename = safename[0:60]

                    json_path = basedir / f"subtitle_{iter_record.subtitle_id}-{safename}-{iter_record.language}{iter_record.extension}.json"
                    file_path = basedir / f"subtitle_{iter_record.subtitle_id}-{safename}-{iter_record.language}{iter_record.extension}"

                    with open(json_path, "w", encoding="utf-8") as f:
                        logger.debug("writing json to `%s`", json_path)
                        f.write(json.dumps(attrs.asdict(iter_record)))

                    with open(file_path, "wb") as f2:
                        logger.debug("writing file to `%s`", file_path)
                        data = await subtitle_dl_result.read()
                        f2.write(data)



                current_page += 1



    def get_user_html(self, element):

        user_td_tag_list = element.select("td:nth-of-type(9)")

        if len(user_td_tag_list) == 0:
            breakpoint()

        user_td_tag = user_td_tag_list[0]

        user_profile_name = None
        user_profile_name_list  = user_td_tag.select("a > span")


        if len(user_profile_name_list) == 0:
            user_profile_name = "ANONYMOUS"
        else:
            user_profile_name = user_profile_name_list[0].text.strip()


        user_group = None
        user_group_list = user_td_tag.select("a > span > i")
        if len(user_group_list) == 0:
            user_group = None
        else:
            user_group = user_group_list[0]["data-original-title"]


        user_profile_link_maybe = None
        user_profile_link_maybe_list =  user_td_tag.select("a")
        if len(user_profile_link_maybe_list) == 0:
           user_profile_link_maybe = None
        else:
            user_profile_link_maybe = user_profile_link_maybe_list[0]["href"]



        user_dict = {
            "profile_link": user_profile_link_maybe,
            "group": user_group,
            "username": user_profile_name}
        return user_dict

    def get_relative_download_time(self, element):
        time_td_tag = element.select("td:nth-of-type(8)")[0]
        return time_td_tag.text

    def get_download_count_str(self, element):
        download_td_tag = element.select("td:nth-of-type(7)")[0]
        return download_td_tag.text

    def get_size_str(self, element):
        size_td_tag = element.select("td:nth-of-type(6)")[0]
        return size_td_tag.text

    def get_extension_string(self, element):
        extension_tag = element.select("td:nth-of-type(5)")[0]
        return extension_tag.text

    def get_download_link(self, element):
        download_a_tag = element.select("td:nth-of-type(4) > a")[0]
        return download_a_tag["href"]

    def get_language_string(self, element):

        language_td_tag = element.select("td:nth-of-type(3)")[0]
        return language_td_tag.text

    def get_title_string(self, element):

        a_tag = element.select("td:nth-of-type(2) > a")[0]
        return a_tag.text


    def get_category_string(self, element):

        i_tag = element.select("td:nth-of-type(1) > a > div > i")[0]
        return i_tag["data-original-title"]