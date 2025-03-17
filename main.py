import re
import aiohttp
import logging
from pathlib import Path
from urllib.parse import urlparse
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("LinkDownloader", "YourName", "智能链接检测与下载插件", "1.0.1")
class LinkDownloader(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.download_dir = Path("data/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "AstrBot-Downloader/1.0"}
        )

    @filter.message()
    async def handle_message(self, event: AstrMessageEvent):
        """检测消息中的有效下载链接"""
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        urls = re.findall(url_pattern, event.message_str)
        
        if not urls:
            return  # 修正异步生成器的返回问题

        results = []
        for url in urls[:3]:  # 限制并发处理数量
            try:
                filename, filesize = await self._download_file(url)
                results.append(f"✅ 下载成功：{filename} ({filesize}MB)")
            except Exception as e:
                logger.error(f"下载失败: {str(e)}", exc_info=True)
                results.append(f"❌ 下载失败：{url.split('?')[0]}")

        if results:
            yield event.plain_result("\n".join(results))

    async def _download_file(self, url: str):
        """异步下载核心逻辑"""
        async with self.session.get(url, allow_redirects=True) as response:
            if response.status != 200:
                raise Exception(f"HTTP错误 {response.status}")

            # 智能文件名识别
            content_disposition = response.headers.get("Content-Disposition", "")
            filename_match = re.findall(r'filename\*?=["\']?(?:UTF-\d["\']*)?([^;"\']*)', content_disposition)
            filename = filename_match[0] if filename_match else Path(urlparse(url).path).name
            filename = filename.strip('"')  # 去除多余引号

            # 安全文件路径处理
            filepath = self.download_dir / self._sanitize_filename(filename)
            
            # 分块写入文件
            total_size = 0
            with open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                    f.write(chunk)
                    total_size += len(chunk)
                    if total_size > 100*1024*1024:  # 100MB限制
                        raise Exception("文件大小超过限制")

            return filename, round(total_size/(1024*1024), 2)

    def _sanitize_filename(self, name: str) -> str:
        """清理非法文件名"""
        return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

    async def terminate(self):
        """安全关闭会话"""
        await self.session.close()
        logger.info("下载会话已安全关闭")
