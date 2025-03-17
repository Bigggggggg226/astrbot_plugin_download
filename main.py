import re
import aiohttp
import os
import time
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from urllib.parse import urlparse

@register("LinkDownloader", "YourName", "自动下载消息中的链接内容", "1.0.0")
class LinkDownloaderPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.download_dir = os.path.join(os.path.dirname(__file__), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        self.allowed_domains = []  # 域名白名单
        self.max_size = 1024 * 1024 * 10  # 10MB

    # 关键修正点：使用正确的message装饰器
    @filter.message()
    async def auto_download(self, event: AstrMessageEvent):
        '''自动检测消息中的链接并下载'''
        urls = re.findall(r'https?://\S+', event.message_str)
        
        if not urls:
            return

        for url in urls:
            try:
                if self.allowed_domains:
                    domain = urlparse(url).netloc
                    if domain not in self.allowed_domains:
                        continue

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        content_size = int(response.headers.get('Content-Length', 0))
                        if 0 < self.max_size < content_size:
                            logger.warning(f"文件过大，跳过下载: {url}")
                            continue

                        filename = os.path.basename(urlparse(url).path)
                        if not filename:
                            filename = f"file_{int(time.time())}"

                        save_path = os.path.join(self.download_dir, filename)
                        with open(save_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                f.write(chunk)

                        logger.info(f"成功下载文件: {save_path}")
                        yield event.plain_result(f"✅ 已自动保存链接内容: {filename}")

            except Exception as e:
                logger.error(f"下载失败: {str(e)}")
                yield event.plain_result(f"❌ 链接下载失败: {url}")

    async def terminate(self):
        logger.info("链接下载插件已被卸载")
