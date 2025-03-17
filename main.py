from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re
from urllib.parse import unquote

@register("dl", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("dl")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        args = event.message_str.split()
        
        if len(args) < 2:
            yield event.plain_result("请提供文件链接，格式：/download <url>")
            return

        url = args[1].strip()
        
        if not re.match(r'^https?://', url, re.IGNORECASE):
            yield event.plain_result("链接格式不正确，请使用http/https协议")
            return

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # 修复点1：添加编码处理
                        filename = self.get_safe_filename(
                            url,
                            response.headers.get("Content-Disposition", "")
                        )
                        
                        # 修复点2：确保文件名使用安全编码
                        file = File(filename, content)
                        yield event.result([file])
                    else:
                        yield event.plain_result(f"下载失败，服务器返回状态码：{response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"下载失败: {str(e)}")
            yield event.plain_result("下载失败，请检查链接有效性或网络连接")
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            yield event.plain_result("下载过程发生意外错误")

    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        """安全获取文件名"""
        filename = ""
        
        # 修复点3：增强Content-Disposition解析
        if content_disposition:
            # 处理带编码的文件名 (RFC 5987)
            if "filename*=" in content_disposition:
                match = re.search(r'filename\*=(?:utf-8|UTF-8)''"?([^;]+)', content_disposition)
                if match:
                    filename = unquote(match.group(1)).decode('utf-8', 'ignore')
            else:
                match = re.search(r'filename=("?)(.*?)\1(?:;|$)', content_disposition)
                if match:
                    filename = unquote(match.group(2)).encode('latin-1').decode('utf-8', 'ignore')

        # 修复点4：URL文件名解码处理
        if not filename:
            path = unquote(url.split('/')[-1].split('?')[0])
            filename = path.encode('latin-1').decode('utf-8', 'ignore') or "downloaded_file"

        # 修复点5：过滤非法字符
        return re.sub(r'[\\/*?:"<>|]', "", filename).strip()[:128] or "file"

    async def terminate(self):
        '''清理资源'''
        logger.info("文件下载插件已卸载")
