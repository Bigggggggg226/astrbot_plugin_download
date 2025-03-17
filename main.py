from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re

@register("download", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("dl")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        # 解析消息内容
        args = event.message_str.split()
        
        # 检查参数有效性
        if len(args) < 2:
            yield event.plain_result("请提供文件链接，格式：/download <url>")
            return

        url = args[1].strip()
        
        # 验证URL格式
        if not re.match(r'^https?://', url, re.IGNORECASE):
            yield event.plain_result("链接格式不正确，请使用http/https协议")
            return

        try:
            # 异步下载文件
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # 获取文件名（优先从Content-Disposition获取）
                        filename = self.get_filename(
                            url,
                            response.headers.get("Content-Disposition", "")
                        )
                        
                        # 创建文件消息组件
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

    def get_filename(self, url: str, content_disposition: str) -> str:
        """通过解析响应头或URL获取文件名"""
        # 从Content-Disposition解析文件名
        if content_disposition:
            match = re.findall("filename=(.+)", content_disposition)
            if match:
                return match[0].strip('"')
        
        # 从URL路径解析文件名
        path = re.split(r"[\\/]", url)[-1]
        if "." in path:
            return path.split("?")[0]  # 去除URL参数
        return "downloaded_file"  # 默认文件名

    async def terminate(self):
        '''清理资源'''
        logger.info("文件下载插件已卸载")
