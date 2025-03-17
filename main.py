from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re
from urllib.parse import unquote, urlparse

@register("dl", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("dl")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        # 关键修复1：使用maxsplit确保URL完整性
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("请提供文件链接，格式：/dl <url>")
            return

        raw_url = args[1].strip()
        
        # 关键修复2：标准化URL处理
        try:
            parsed = urlparse(raw_url)
            if not parsed.scheme:
                raw_url = "http://" + raw_url
                parsed = urlparse(raw_url)
            url = parsed.geturl()
        except Exception as e:
            logger.error(f"URL解析失败: {raw_url} - {str(e)}")
            yield event.plain_result("链接格式无效，请确认包含完整协议头")
            return

        # 关键修复3：添加浏览器级请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        try:
            async with aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                # 关键修复4：先发送HEAD请求验证
                async with session.head(url, allow_redirects=True) as head_resp:
                    if head_resp.status != 200:
                        yield event.plain_result(f"资源验证失败（HTTP {head_resp.status}），实际请求路径：{head_resp.url}")
                        return
                    
                    # 关键修复5：处理跳转后的真实URL
                    real_url = str(head_resp.url)
                
                # 使用验证后的URL进行下载
                async with session.get(real_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        filename = self.get_safe_filename(real_url, response.headers.get("Content-Disposition", ""))
                        file = File(filename, content)
                        yield event.result([file])
                    else:
                        logger.warning(f"最终下载失败: {real_url} - {response.status}")
                        yield event.plain_result(f"服务器最终返回异常状态码：{response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"网络错误: {str(e)}")
            yield event.plain_result(f"网络连接异常：{str(e)}")
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            yield event.plain_result("下载过程发生意外错误")

    # 保持原有的安全文件名处理方法
    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        ...

    async def terminate(self):
        '''清理资源'''
        logger.info("文件下载插件已卸载")
