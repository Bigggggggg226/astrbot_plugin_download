from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import aiohttp
import re

@register("link-downloader", "Your Name", "自动检测并下载链接内容的插件", "1.0.0", "repo url")
class LinkDownloaderPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def download_content(self, session, url):
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                return None

    @filter.message()
    async def on_message(self, event: AstrMessageEvent):
        message = event.message_str
        urls = self.extract_urls(message)
        
        if urls:
            async with aiohttp.ClientSession() as session:
                for url in urls:
                    content = await self.download_content(session, url)
                    if content:
                        yield event.plain_result(f"已成功下载内容（部分预览）:\n{content[:100]}...")
                    else:
                        yield event.plain_result(f"无法下载 {url} 的内容。")

    def extract_urls(self, text):
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\$$\$$,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
