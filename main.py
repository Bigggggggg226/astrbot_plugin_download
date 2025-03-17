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
        logger.debug(f"原始输入: {event.message_str}")
        args = event.message_str.split(maxsplit=1)
        
        if len(args) < 2:
            logger.warning("缺少URL参数")
            yield event.plain_result("请提供文件链接，格式：/dl <url>")
            return

        raw_url = args[1].strip()
        logger.debug(f"原始URL: {raw_url}")

        try:
            # URL标准化处理
            parsed = urlparse(raw_url)
            if not parsed.scheme:
                logger.debug("自动补全HTTP协议头")
                raw_url = "http://" + raw_url
                parsed = urlparse(raw_url)
            
            if not parsed.netloc:
                logger.error("缺少有效域名")
                raise ValueError("Invalid domain")
                
            url = parsed.geturl()
            logger.debug(f"解析后URL: {url}")
            
        except Exception as e:
            logger.error(f"URL解析失败: {str(e)}")
            yield event.plain_result("链接格式无效，请确认包含完整协议头（如http://或https://）")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Referer": url
        }
        logger.debug(f"请求头: {headers}")

        try:
            async with aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                # 调试阶段先禁用HEAD请求
                logger.debug("正在发送GET请求...")
                
                async with session.get(
                    url,
                    allow_redirects=True,
                    raise_for_status=False
                ) as response:
                    logger.debug(f"响应状态: {response.status}")
                    logger.debug(f"响应头: {dict(response.headers)}")
                    logger.debug(f"最终URL: {str(response.url)}")
                    
                    if response.status == 200:
                        logger.debug("开始读取内容...")
                        content = await response.read()
                        logger.debug(f"获取内容长度: {len(content)}字节")
                        
                        filename = self.get_safe_filename(
                            str(response.url),
                            response.headers.get("Content-Disposition", "")
                        )
                        logger.debug(f"生成文件名: {filename}")
                        
                        file = File(filename, content)
                        yield event.result([file])
                    else:
                        logger.warning(f"异常状态码: {response.status}")
                        yield event.plain_result(
                            f"请求失败（HTTP {response.status}）\n"
                            f"最终路径：{response.url}\n"
                            f"建议用浏览器测试该链接"
                        )

        except aiohttp.ClientError as e:
            logger.error(f"网络错误详情: {type(e)} - {str(e)}")
            yield event.plain_result(f"网络连接异常：{str(e)}")
        except Exception as e:
            logger.exception("未知错误详情:")
            yield event.plain_result("下载过程发生意外错误")

    def get_safe_filename(self, url: str, content_disposition: str) -> str:
        logger.debug(f"文件名解析输入 - URL: {url} | Content-Disposition: {content_disposition}")
        # 保持原有解析逻辑
        return "file"

    async def terminate(self):
        logger.info("插件已卸载")

# 在配置中启用调试模式（需要机器人支持）
# logger.setLevel("DEBUG")
