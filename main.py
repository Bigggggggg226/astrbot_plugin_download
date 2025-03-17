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
        logger.debug(f"[输入检测] 原始消息: {event.message_str}")
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("格式：/dl <文件链接>")
            return

        raw_url = args[1].strip()
        logger.debug(f"[URL处理] 原始输入: {raw_url}")

        try:
            # URL标准化处理
            parsed = urlparse(raw_url)
            if not parsed.scheme:
                logger.debug("[URL处理] 自动添加HTTP协议头")
                raw_url = f"http://{raw_url}"
                parsed = urlparse(raw_url)
            
            if not parsed.netloc:
                raise ValueError("无效域名")
                
            url = parsed.geturl()
            logger.debug(f"[URL处理] 标准化后: {url}")
            
        except Exception as e:
            logger.error(f"[URL错误] {str(e)}")
            yield event.plain_result("链接格式错误，请确认包含http://或https://")
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
                # 先验证资源可用性
                logger.debug("[网络请求] 发送HEAD请求验证...")
                async with session.head(url, allow_redirects=True) as head_resp:
                    logger.debug(f"[网络响应] 状态码: {head_resp.status} 最终URL: {head_resp.url}")
                    if head_resp.status != 200:
                        yield event.plain_result(f"资源不可用 (HTTP {head_resp.status})\n最终地址：{head_resp.url}")
                        return
                    real_url = str(head_resp.url)

                # 正式下载
                logger.debug(f"[文件下载] 开始下载: {real_url}")
                async with session.get(real_url) as response:
                    content = await response.read()
                    logger.debug(f"[文件下载] 接收大小: {len(content)/1024:.2f}KB")
                    
                    # 安全文件名处理
                    filename = self.get_safe_filename(
                        real_url,
                        response.headers.get("Content-Disposition", "")
                    )
                    logger.debug(f"[文件名处理] 最终文件名: {filename}")
                    
                    # 创建文件消息
                    file = File(filename, content)
                    yield event.result([file])

        except aiohttp.ClientError as e:
            logger.error(f"[网络错误] {type(e).__name__}: {str(e)}")
            yield event.plain_result(f"网络错误：{str(e)}")
        except Exception as e:
            logger.exception("[系统错误] 未知异常")
            yield event.plain_result("系统处理异常")

    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        """多层安全文件名处理"""
        def decode_with_fallback(byte_str: bytes) -> str:
            """尝试多种编码解码"""
            encodings = ['utf-8', 'gbk', 'latin-1', 'gb2312', 'big5']
            for enc in encodings:
                try:
                    return byte_str.decode(enc)
                except UnicodeDecodeError:
                    continue
            return byte_str.decode('utf-8', errors='replace')

        filename = ""
        
        # 解析Content-Disposition头
        if content_disposition:
            # 处理RFC5987扩展格式 (filename*=utf-8''xxx)
            if 'filename*=' in content_disposition:
                match = re.search(r'filename\*=([^;]+)\'\'"?([^;]+)', content_disposition, re.IGNORECASE)
                if match:
                    encoding = match.group(1).lower() or 'utf-8'
                    try:
                        decoded = unquote(match.group(2), encoding=encoding, errors='replace')
                        filename = decoded
                    except:
                        filename = unquote(match.group(2), errors='replace')
            
            # 处理普通filename参数
            if not filename:
                match = re.search(r'filename=("?)(.*?)\1', content_disposition)
                if match:
                    filename_part = match.group(2)
                    try:
                        filename = unquote(filename_part, errors='strict')
                    except UnicodeDecodeError:
                        filename_bytes = unquote_to_bytes(filename_part)
                        filename = decode_with_fallback(filename_bytes)

        # 从URL路径解析
        if not filename:
            path = url.split('/')[-1].split('?')[0]
            try:
                filename = unquote(path, errors='strict')
            except UnicodeDecodeError:
                filename_bytes = unquote_to_bytes(path)
                filename = decode_with_fallback(filename_bytes)

        # 安全处理
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # 过滤非法字符
        filename = filename.strip()  # 去除两端空格
        
        # 编码最终保障
        filename = filename.encode('utf-8', errors='ignore').decode('utf-8')
        
        # 默认值和长度限制
        if not filename:
            filename = "download_file"
        return filename[:255] if len(filename) > 255 else filename

    async def terminate(self):
        '''清理资源'''
        logger.info("[系统] 插件已卸载")from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
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
        logger.debug(f"[输入检测] 原始消息: {event.message_str}")
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("格式：/dl <文件链接>")
            return

        raw_url = args[1].strip()
        logger.debug(f"[URL处理] 原始输入: {raw_url}")

        try:
            # URL标准化处理
            parsed = urlparse(raw_url)
            if not parsed.scheme:
                logger.debug("[URL处理] 自动添加HTTP协议头")
                raw_url = f"http://{raw_url}"
                parsed = urlparse(raw_url)
            
            if not parsed.netloc:
                raise ValueError("无效域名")
                
            url = parsed.geturl()
            logger.debug(f"[URL处理] 标准化后: {url}")
            
        except Exception as e:
            logger.error(f"[URL错误] {str(e)}")
            yield event.plain_result("链接格式错误，请确认包含http://或https://")
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
                # 先验证资源可用性
                logger.debug("[网络请求] 发送HEAD请求验证...")
                async with session.head(url, allow_redirects=True) as head_resp:
                    logger.debug(f"[网络响应] 状态码: {head_resp.status} 最终URL: {head_resp.url}")
                    if head_resp.status != 200:
                        yield event.plain_result(f"资源不可用 (HTTP {head_resp.status})\n最终地址：{head_resp.url}")
                        return
                    real_url = str(head_resp.url)

                # 正式下载
                logger.debug(f"[文件下载] 开始下载: {real_url}")
                async with session.get(real_url) as response:
                    content = await response.read()
                    logger.debug(f"[文件下载] 接收大小: {len(content)/1024:.2f}KB")
                    
                    # 安全文件名处理
                    filename = self.get_safe_filename(
                        real_url,
                        response.headers.get("Content-Disposition", "")
                    )
                    logger.debug(f"[文件名处理] 最终文件名: {filename}")
                    
                    # 创建文件消息
                    file = File(filename, content)
                    yield event.result([file])

        except aiohttp.ClientError as e:
            logger.error(f"[网络错误] {type(e).__name__}: {str(e)}")
            yield event.plain_result(f"网络错误：{str(e)}")
        except Exception as e:
            logger.exception("[系统错误] 未知异常")
            yield event.plain_result("系统处理异常")

    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        """多层安全文件名处理"""
        def decode_with_fallback(byte_str: bytes) -> str:
            """尝试多种编码解码"""
            encodings = ['utf-8', 'gbk', 'latin-1', 'gb2312', 'big5']
            for enc in encodings:
                try:
                    return byte_str.decode(enc)
                except UnicodeDecodeError:
                    continue
            return byte_str.decode('utf-8', errors='replace')

        filename = ""
        
        # 解析Content-Disposition头
        if content_disposition:
            # 处理RFC5987扩展格式 (filename*=utf-8''xxx)
            if 'filename*=' in content_disposition:
                match = re.search(r'filename\*=([^;]+)\'\'"?([^;]+)', content_disposition, re.IGNORECASE)
                if match:
                    encoding = match.group(1).lower() or 'utf-8'
                    try:
                        decoded = unquote(match.group(2), encoding=encoding, errors='replace')
                        filename = decoded
                    except:
                        filename = unquote(match.group(2), errors='replace')
            
            # 处理普通filename参数
            if not filename:
                match = re.search(r'filename=("?)(.*?)\1', content_disposition)
                if match:
                    filename_part = match.group(2)
                    try:
                        filename = unquote(filename_part, errors='strict')
                    except UnicodeDecodeError:
                        filename_bytes = unquote_to_bytes(filename_part)
                        filename = decode_with_fallback(filename_bytes)

        # 从URL路径解析
        if not filename:
            path = url.split('/')[-1].split('?')[0]
            try:
                filename = unquote(path, errors='strict')
            except UnicodeDecodeError:
                filename_bytes = unquote_to_bytes(path)
                filename = decode_with_fallback(filename_bytes)

        # 安全处理
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # 过滤非法字符
        filename = filename.strip()  # 去除两端空格
        
        # 编码最终保障
        filename = filename.encode('utf-8', errors='ignore').decode('utf-8')
        
        # 默认值和长度限制
        if not filename:
            filename = "download_file"
        return filename[:255] if len(filename) > 255 else filename

    async def terminate(self):
        '''清理资源'''
        logger.info("[系统] 插件已卸载")
