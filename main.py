from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re
from urllib.parse import unquote, urlparse, unquote_to_bytes

@register("dl", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("dl")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        logger.debug(f"[Input] Raw message: {event.message_str}")
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("Usage: /dl <url>")
            return

        raw_url = args[1].strip()
        logger.debug(f"[URL] Original input: {raw_url}")

        try:
            parsed = urlparse(raw_url)
            if not parsed.scheme:
                logger.debug("[URL] Adding HTTP protocol")
                raw_url = f"http://{raw_url}"
                parsed = urlparse(raw_url)
            
            if not parsed.netloc:
                raise ValueError("Invalid domain")
                
            url = parsed.geturl()
            logger.debug(f"[URL] Normalized: {url}")
            
        except Exception as e:
            logger.error(f"[URL Error] {str(e)}")
            yield event.plain_result("Invalid URL format")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Referer": url
        }

        try:
            async with aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                logger.debug("[Network] Sending HEAD request")
                async with session.head(url, allow_redirects=True) as head_resp:
                    logger.debug(f"[Network] HEAD response: {head_resp.status} {head_resp.url}")
                    if head_resp.status != 200:
                        yield event.plain_result(f"Resource unavailable (HTTP {head_resp.status})\nFinal URL: {head_resp.url}")
                        return
                    real_url = str(head_resp.url)

                logger.debug(f"[Download] Starting GET: {real_url}")
                async with session.get(real_url) as response:
                    content = await response.read()
                    logger.debug(f"[Download] Received: {len(content)/1024:.2f}KB")
                    
                    filename = self.get_safe_filename(
                        real_url,
                        response.headers.get("Content-Disposition", "")
                    )
                    logger.debug(f"[Filename] Final: {filename}")
                    
                    file = File(filename, content)
                    yield event.result([file])

        except aiohttp.ClientError as e:
            logger.error(f"[Network Error] {type(e).__name__}: {str(e)}")
            yield event.plain_result(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("[System Error] Unexpected exception")
            yield event.plain_result("System error occurred")

    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        def decode_with_fallback(byte_str: bytes) -> str:
            encodings = ['utf-8', 'gbk', 'latin-1', 'gb2312', 'big5']
            for enc in encodings:
                try:
                    return byte_str.decode(enc)
                except UnicodeDecodeError:
                    continue
            return byte_str.decode('utf-8', errors='replace')

        filename = ""
        
        if content_disposition:
            if 'filename*=' in content_disposition:
                match = re.search(r'filename\*=([^;]+)\'\'"?([^;]+)', content_disposition, re.IGNORECASE)
                if match:
                    try:
                        decoded = unquote(match.group(2), encoding=match.group(1), errors='replace')
                        filename = decoded
                    except:
                        filename = unquote(match.group(2), errors='replace')
            
            if not filename:
                match = re.search(r'filename=("?)(.*?)\1', content_disposition)
                if match:
                    filename_part = match.group(2)
                    try:
                        filename = unquote(filename_part, errors='strict')
                    except UnicodeDecodeError:
                        filename_bytes = unquote_to_bytes(filename_part)
                        filename = decode_with_fallback(filename_bytes)

        if not filename:
            path = url.split('/')[-1].split('?')[0]
            try:
                filename = unquote(path, errors='strict')
            except UnicodeDecodeError:
                filename_bytes = unquote_to_bytes(path)
                filename = decode_with_fallback(filename_bytes)

        filename = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        filename = filename.encode('utf-8', errors='ignore').decode('utf-8')
        
        if not filename:
            filename = "download_file"
        return filename[:255] if len(filename) > 255 else filename

    async def terminate(self):
        logger.info("[System] Plugin unloaded")
