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
            yield event.plain_result("链接格式无效，请确认包含完整协议头")
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
                logger.debug("[网络请求] 发送HEAD请求验证...")
                async with session.head(url, allow_redirects=True) as head_resp:
                    logger.debug(f"[网络响应] 状态码: {head_resp.status} 最终URL: {head_resp.url}")
                    if head_resp.status != 200:
                        yield event.plain_result(f"资源不可用 (HTTP {head_resp.status})\n最终地址：{head_resp.url}")
                        return
                    real_url = str(head_resp.url)

                logger.debug(f"[文件下载] 开始下载: {real_url}")
                async with session.get(real_url) as response:
                    content = await response.read()
                    logger.debug(f"[文件下载] 接收大小: {len(content)/1024:.2f}KB")
                    
                    filename = self.get_ultimate_safe_filename(
                        real_url,
                        response.headers.get("Content-Disposition", "")
                    )
                    logger.debug(f"[文件名处理] 最终文件名: {filename}")
                    
                    file = File(filename, content)
                    yield event.result([file])

        except aiohttp.ClientError as e:
            logger.error(f"[网络错误] {type(e).__name__}: {str(e)}")
            yield event.plain_result(f"网络连接异常：{str(e)}")
        except Exception as e:
            logger.exception("[系统错误] 未知异常")
            yield event.plain_result("系统处理异常")

    def get_ultimate_safe_filename(self, url: str, content_disposition: str) -> str:
        """终极安全文件名处理方案"""
        def strict_decode(data: bytes) -> str:
            """四重编码回退策略"""
            for enc in ('utf-8', 'gbk', 'latin-1', 'gb2312'):
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode('utf-8', errors='replace').replace('\ufffd', '_')

        def sanitize_name(name: str) -> str:
            """严格字符白名单过滤"""
            allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. ")
            return ''.join([c if c in allowed else '_' for c in name]).strip()

        # 第一阶段：原始数据获取
        filename = ""
        
        # 解析Content-Disposition头
        if content_disposition:
            try:
                # RFC 5987扩展处理
                if 'filename*=' in content_disposition:
                    match = re.search(r'filename\*=([^;]+)\'\'"?([^;]+)', content_disposition, re.IGNORECASE)
                    if match:
                        encoding = match.group(1).lower() or 'utf-8'
                        decoded_bytes = unquote_to_bytes(match.group(2))
                        filename = strict_decode(decoded_bytes)
                
                # 普通filename参数处理
                if not filename:
                    match = re.search(r'filename=("?)(.*?)\1', content_disposition)
                    if match:
                        decoded_bytes = unquote_to_bytes(match.group(2))
                        filename = strict_decode(decoded_bytes)
            except Exception as e:
                logger.error(f"[文件名解析] Content-Disposition处理失败: {str(e)}")

        # 从URL路径解析
        if not filename:
            try:
                path_part = url.split('/')[-1].split('?')[0]
                decoded_bytes = unquote_to_bytes(path_part)
                filename = strict_decode(decoded_bytes)
            except Exception as e:
                logger.error(f"[文件名解析] URL路径处理失败: {str(e)}")
                filename = "download_file"

        # 第二阶段：终极净化处理
        filename = sanitize_name(filename)
        
        # 第三阶段：强制UTF-8合规
        final_name = filename.encode('utf-8', errors='replace').decode('utf-8')
        final_name = re.sub(r'_+', '_', final_name)  # 合并连续下划线
        
        # 默认值和长度限制
        if not final_name.strip('._'):
            final_name = "file_" + str(int(time.time()))
        return final_name[:100]  # 保守长度限制

    async def terminate(self):
        logger.info("[系统] 插件已卸载")
