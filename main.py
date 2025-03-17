from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re
import time
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
                    
                    filename = self.ultimate_filename_processor(
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

    def ultimate_filename_processor(self, url: str, content_disposition: str) -> str:
        """五层防护文件名处理器"""
        # 编码优先级列表（扩展版）
        ENCODING_PRIORITY = [
            'utf-8', 'gbk', 'gb18030', 'big5',
            'shift_jis', 'euc-kr', 'iso-8859-1',
            'windows-1252', 'utf-16'
        ]

        def advanced_decode(byte_data: bytes) -> str:
            """智能解码器"""
            for encoding in ENCODING_PRIORITY:
                try:
                    decoded = byte_data.decode(encoding, errors='strict')
                    # 有效性验证：排除控制字符（保留空格）
                    if all(ord(c) >= 0x20 or c in ('\n', '\r', '\t') for c in decoded):
                        return decoded
                except (UnicodeDecodeError, LookupError):
                    continue
            # 最终回退策略
            return byte_data.decode('utf-8', errors='replace').replace('\ufffd', '_')

        def sanitize_filename(name: str) -> str:
            """安全字符过滤器"""
            # 允许：中文、日文、韩文、基本拉丁字母、数字、常用符号
            pattern = re.compile(
                r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7a3\-_.() ]',
                re.UNICODE
            )
            sanitized = pattern.sub('_', name)
            # 清理连续特殊字符
            return re.sub(r'[_]{2,}', '_', sanitized).strip('_')

        # 阶段1：内容协商处理
        filename = ""
        if content_disposition:
            # 处理RFC5987扩展格式
            if 'filename*=' in content_disposition:
                match = re.search(r'filename\*=([^;]+)\'\'"?([^;]+)', content_disposition, re.I)
                if match:
                    try:
                        encoding_part = match.group(1).lower()
                        value_part = match.group(2)
                        decoded_bytes = unquote_to_bytes(value_part)
                        filename = advanced_decode(decoded_bytes)
                        logger.debug(f"[RFC5987解析] 检测到编码:{encoding_part} 原始值:{value_part}")
                    except Exception as e:
                        logger.error(f"[RFC5987错误] {str(e)}")

            # 处理普通filename参数
            if not filename:
                match = re.search(r'filename=("?)(.*?)\1', content_disposition)
                if match:
                    try:
                        raw_value = unquote_to_bytes(match.group(2))
                        filename = advanced_decode(raw_value)
                    except Exception as e:
                        logger.error(f"[普通参数解析错误] {str(e)}")

        # 阶段2：URL路径解析
        if not filename:
            try:
                path_segment = url.split('/')[-1].split('?')[0]
                decoded_bytes = unquote_to_bytes(path_segment)
                filename = advanced_decode(decoded_bytes)
                logger.debug(f"[URL路径解析] 原始路径:{path_segment}")
            except Exception as e:
                logger.error(f"[URL解析错误] {str(e)}")

        # 阶段3：深度清洗
        filename = sanitize_filename(filename or "")
        
        # 阶段4：强制UTF-8合规化
        final_name = filename.encode('utf-8', errors='replace').decode('utf-8')
        final_name = re.sub(r'\s+', ' ', final_name)  # 标准化空白字符

        # 阶段5：最终保障
        if not final_name or len(final_name.encode('utf-8')) > 255:
            timestamp = int(time.time())
            final_name = f"file_{timestamp}"
        
        return final_name[:220]  # 预留UTF-8多字节空间

    async def terminate(self):
        logger.info("[系统] 插件已卸载")
