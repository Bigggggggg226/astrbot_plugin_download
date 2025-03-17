from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from aiocqhttp.message import MessageSegment  # 添加aiocqhttp的消息组件
import aiohttp
import re

@register("download", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("download")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        args = event.message_str.split()
        
        if len(args) < 2:
            await event.reply("请提供文件链接，格式：/download <url>")
            return

        url = args[1].strip()
        
        if not re.match(r'^https?://', url, re.IGNORECASE):
            await event.reply("链接格式不正确，请使用http/https协议")
            return

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        filename = self.get_filename(
                            url,
                            response.headers.get("Content-Disposition", "")
                        )
                        
                        # 使用aiocqhttp的文件发送方式
                        file_msg = MessageSegment.file(filename, content)
                        await event.reply(file_msg)
                    else:
                        await event.reply(f"下载失败，服务器返回状态码：{response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"下载失败: {str(e)}")
            await event.reply("下载失败，请检查链接有效性或网络连接")
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            await event.reply("下载过程发生意外错误")

    def get_filename(self, url: str, content_disposition: str) -> str:
        if content_disposition:
            match = re.findall("filename=(.+)", content_disposition)
            if match:
                return match[0].strip('"')
        
        path = re.split(r"[\\/]", url)[-1]
        if "." in path:
            return path.split("?")[0]
        return "downloaded_file"

    async def terminate(self):
        logger.info("文件下载插件已卸载")
