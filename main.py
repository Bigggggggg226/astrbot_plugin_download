import re
import aiohttp
from pathlib import Path
from urllib.parse import urlparse
from astrbot.api.event import AstrMessageEvent, MessageEventFilter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("LinkDownloader", "YourName", "智能链接下载插件", "1.0.2")
class LinkDownloader(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.download_dir = Path("data/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "AstrBot-Downloader/1.2"}
        )

    @MessageEventFilter.message()
    async def handle_message(self, event: AstrMessageEvent):
        """链接消息处理器"""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+\S+'
        urls = re.findall(url_pattern, event.message_str)
        
        if not urls:
            return

        results = []
        for url in urls[:3]:  # 限制最大处理数
            try:
                filename, size = await self._download(url)
                results.append(f"✅ 下载完成：{filename} ({size}MB)")
            except Exception as e:
                results.append(f"❌ 下载失败：{str(e)}")
                logger.error(f"下载异常：{url}", exc_info=True)

        yield event.reply("\n".join(results))

    async def _download(self, url: str) -> tuple[str, float]:
        """执行下载操作"""
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            
            # 文件名处理
            filename = self._get_filename(resp, url)
            filepath = self.download_dir / self._sanitize(filename)
            
            # 分块写入
            total = 0
            with open(filepath, 'wb') as f:
                async for chunk in resp.content.iter_chunked(1_048_576):  # 1MB/chunk
                    f.write(chunk)
                    total += len(chunk)
                    if total > 100_000_000:  # 100MB限制
                        raise Exception("文件超过大小限制")
            
            return filename, round(total / 1_048_576, 2)

    def _get_filename(self, resp, url: str) -> str:
        """获取安全文件名"""
        if cd := resp.headers.get("Content-Disposition"):
            if match := re.search(r'filename\*?=["\']?(?:UTF-\d["\']*)?([^;"\']+)', cd):
                return match.group(1).strip('"')
        return Path(urlparse(url).path).name or "unnamed_file"

    def _sanitize(self, name: str) -> str:
        """清理危险字符"""
        return re.sub(r'[\\/:*?"<>|]', "_", name).strip()

    async def terminate(self):
        """关闭资源"""
        await self.session.close()
        logger.info("下载器已安全关闭")
