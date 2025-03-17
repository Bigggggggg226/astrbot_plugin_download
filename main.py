from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import File
from astrbot.api import logger
import aiohttp
import re
from urllib.parse import unquote, urlparse

@register("download", "YourName", "文件下载插件", "1.0.0")
class DownloadPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("download")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("请提供文件链接，格式：/download <url>")
            return

        raw_url = args[1].strip()
        
        # 增强URL验证
        try:
            parsed = urlparse(raw_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError
            url = parsed.geturl()
        except:
            yield event.plain_result("链接格式无效，请确认包含协议头（http/https）和有效域名")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    # 处理特殊状态码
                    if response.status == 404:
                        yield event.plain_result(f"资源不存在（404），请检查链接有效性：\n{url}")
                        return
                        
                    if response.status == 403:
                        yield event.plain_result("访问被拒绝（403），可能需要登录或验证")
                        return

                    if response.status == 200:
                        content = await response.read()
                        filename = self.get_safe_filename(url, response.headers.get("Content-Disposition", ""))
                        file = File(filename, content)
                        yield event.result([file])
                    else:
                        yield event.plain_result(f"下载失败，服务器返回状态码：{response.status}\n可能原因：{self.get_status_hint(response.status)}")

        except aiohttp.ClientConnectionError:
            yield event.plain_result("无法连接服务器，请检查网络或域名解析")
        except aiohttp.ClientSSLError:
            yield event.plain_result("SSL证书验证失败，尝试添加`?insecure`参数跳过验证")
        except Exception as e:
            logger.error(f"下载错误：{str(e)}")
            yield event.plain_result(f"下载失败：{str(e)}")

    def get_status_hint(self, status_code: int) -> str:
        hints = {
            400: "请求格式错误",
            401: "需要身份验证",
            403: "访问被禁止",
            404: "资源不存在",
            405: "请求方法不被允许",
            408: "请求超时",
            429: "请求过于频繁",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时"
        }
        return hints.get(status_code, "未知错误类型")

    # 保留之前的文件名安全处理方法
    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        ...

    async def terminate(self):
        '''清理资源'''
        logger.info("文件下载插件已卸载")from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
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
    
    @filter.command("download")
    async def download_file(self, event: AstrMessageEvent):
        '''从指定URL下载文件'''
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            yield event.plain_result("请提供文件链接，格式：/download <url>")
            return

        raw_url = args[1].strip()
        
        # 增强URL验证
        try:
            parsed = urlparse(raw_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError
            url = parsed.geturl()
        except:
            yield event.plain_result("链接格式无效，请确认包含协议头（http/https）和有效域名")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    # 处理特殊状态码
                    if response.status == 404:
                        yield event.plain_result(f"资源不存在（404），请检查链接有效性：\n{url}")
                        return
                        
                    if response.status == 403:
                        yield event.plain_result("访问被拒绝（403），可能需要登录或验证")
                        return

                    if response.status == 200:
                        content = await response.read()
                        filename = self.get_safe_filename(url, response.headers.get("Content-Disposition", ""))
                        file = File(filename, content)
                        yield event.result([file])
                    else:
                        yield event.plain_result(f"下载失败，服务器返回状态码：{response.status}\n可能原因：{self.get_status_hint(response.status)}")

        except aiohttp.ClientConnectionError:
            yield event.plain_result("无法连接服务器，请检查网络或域名解析")
        except aiohttp.ClientSSLError:
            yield event.plain_result("SSL证书验证失败，尝试添加`?insecure`参数跳过验证")
        except Exception as e:
            logger.error(f"下载错误：{str(e)}")
            yield event.plain_result(f"下载失败：{str(e)}")

    def get_status_hint(self, status_code: int) -> str:
        hints = {
            400: "请求格式错误",
            401: "需要身份验证",
            403: "访问被禁止",
            404: "资源不存在",
            405: "请求方法不被允许",
            408: "请求超时",
            429: "请求过于频繁",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时"
        }
        return hints.get(status_code, "未知错误类型")

    # 保留之前的文件名安全处理方法
    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        ...

    async def terminate(self):
        '''清理资源'''
        logger.info("文件下载插件已卸载")
