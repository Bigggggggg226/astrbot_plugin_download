import re
import os
import aiohttp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from urllib.parse import urlparse
from pathlib import Path

@register("LinkDownloader", "YourName", "链接检测与自动下载插件", "1.0.0")
class LinkDownloader(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.download_dir = Path("data/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    @filter.message()
    async def handle_message(self, event: AstrMessageEvent):
        """检测消息中的链接并触发下载"""
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', event.message_str)
        
        if not urls:
            return False, None

        results = []
        for url in urls[:3]:  # 限制每次最多处理3个链接
            try:
                filename, filesize = await self.download_file(url)
                results.append(f"✅ 下载成功：{filename} ({filesize}MB)")
            except Exception as e:
                results.append(f"❌ 下载失败：{str(e)}")
        
        yield event.plain_result("\n".join(results))

    async def download_file(self, url):
        """异步下载文件"""
        async with self.session.get(url, allow_redirects=True) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            # 获取文件名
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = re.findall(r'filename="?(.+?)"?(;|$)', content_disposition)
            filename = filename[0][0] if filename else Path(urlparse(url).path).name
            
            # 保存文件
            filepath = self.download_dir / filename
            total_size = 0
            with open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024):
                    f.write(chunk)
                    total_size += len(chunk)
            
            return filename, round(total_size / (1024*1024), 2)

    async def terminate(self):
        """关闭会话"""
        await self.session.close()
