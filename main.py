import re
import os
import aiohttp
import aiofiles
import urllib.parse
from astrbot.core import Star, register
from astrbot.message_components import Plain

# 注册插件，替换为您自己的元数据
@register("downloader", "Your Name", "A plugin to download files from links detected in messages", "1.0.0", "https://github.com/yourusername/astrbot_plugin_downloader")
class Downloader(Star):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置下载目录
        self.downloads_dir = 'data/plugins/astrbot_plugin_downloader/downloads'
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    # 监听消息
    async def on_message(self, event):
        message_chain = event.message_chain
        for component in message_chain:
            if isinstance(component, Plain):  # 检查消息组件是否为纯文本
                text = component.text
                # 检测链接
                urls = re.findall(r'https?://[^\s]+', text)
                for url in urls:
                    if await self.is_file(url):  # 判断是否为文件
                        await self.download_file(url)  # 下载文件

    # 判断链接是否指向文件
    async def is_file(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    # 如果不是文本类型，认为是文件
                    if 'text' not in content_type:
                        return True
                    return False
        except:
            return False

    # 下载文件
    async def download_file(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # 从 Content-Disposition 获取文件名
                        content_disposition = response.headers.get('Content-Disposition', '')
                        if content_disposition:
                            _, params = content_disposition.split(';', 1)
                            filename = params.strip().split('=')[1].strip('"')
                        else:
                            # 从 URL 中提取文件名
                            parsed_url = urllib.parse.urlparse(url)
                            filename = parsed_url.path.split('/')[-1]
                            if not filename:
                                filename = 'unknown_file'
                        path = os.path.join(self.downloads_dir, filename)
                        # 检查文件是否已存在
                        if os.path.exists(path):
                            print(f'File already exists: {path}')
                            return
                        # 写入文件
                        async with aiofiles.open(path, 'wb') as f:
                            await f.write(await response.read())
                        print(f'Downloaded {url} to {path}')
                    else:
                        print(f'Failed to download {url}: HTTP {response.status}')
        except Exception as e:
            print(f'Error downloading {url}: {e}')
