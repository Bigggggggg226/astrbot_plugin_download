import re
import os
import aiohttp
import aiofiles
import urllib.parse
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

@register("downloader", "Your Name", "A plugin to download files from links detected in messages", "1.0.0", "https://github.com/yourusername/astrbot_plugin_downloader")
class Downloader(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.downloads_dir = 'data/plugins/astrbot_plugin_downloader/downloads'
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    @filter.message_type(AstrMessageEvent)
    async def on_message(self, event: AstrMessageEvent) -> MessageEventResult:
        message_chain = event.message_chain
        for component in message_chain:
            if isinstance(component, Plain):
                text = component.text
                urls = re.findall(r'https?://[^\s]+', text)
                for url in urls:
                    if await self.is_file(url):
                        await self.download_file(url)
        return MessageEventResult()

    async def is_file(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    if 'text' not in content_type:
                        return True
                    return False
        except:
            return False

    async def download_file(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_disposition = response.headers.get('Content-Disposition', '')
                        if content_disposition:
                            _, params = content_disposition.split(';', 1)
                            filename = params.strip().split('=')[1].strip('"')
                        else:
                            parsed_url = urllib.parse.urlparse(url)
                            filename = parsed_url.path.split('/')[-1]
                            if not filename:
                                filename = 'unknown_file'
                        path = os.path.join(self.downloads_dir, filename)
                        if os.path.exists(path):
                            print(f'File already exists: {path}')
                            return
                        async with aiofiles.open(path, 'wb') as f:
                            await f.write(await response.read())
                        print(f'Downloaded {url} to {path}')
                    else:
                        print(f'Failed to download {url}: HTTP {response.status}')
        except Exception as e:
            print(f'Error downloading {url}: {e}')
