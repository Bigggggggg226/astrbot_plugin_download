from astrbot.api.all import *
import aiohttp
import re

@register("link-downloader", "Your Name", "自动检测并下载链接内容的插件", "1.0.0", "repo_url")
class LinkDownloaderPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.all()  # 监听所有事件
    async def on_event(self, event):
        if not isinstance(event, AstrMessageEvent):
            return
        urls = self.extract_urls(event.message_str)
        if urls:
            async with aiohttp.ClientSession() as session:
                for url in urls:
                    content = await self.download_content(session, url)
                    if content:
                        yield event.plain_result(f"已下载内容（前100字节）: {content[:100]}...")

    def extract_urls(self, text):
        url_pattern = re.compile(r'https?://[^\s]+')
        return url_pattern.findall(text)

    async def download_content(self, session, url):
        try:
            async with session.get(url, timeout=10) as response:
                return await response.read() if response.status == 200 else None
        except Exception as e:
            return None
