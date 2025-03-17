from astrbot.api.all import *
import re
import requests
import os
import time

@register("download_link", "Your Name", "Downloads files from links in messages", "1.0.0")
class DownloadLinkPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.download_path = 'downloads/'
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def handle_message(self, event):
        message = event.message
        urls = re.findall(r'https?://\S+', message)
        for url in urls:
            if self.download_file(url):
                self.send_message(event, f"Downloaded {url}")
            else:
                self.send_message(event, f"Failed to download {url}")

    def download_file(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                filename = url.split('/')[-1]
                if not filename:
                    parts = url.split('/')
                    if parts[-1] == '':
                        filename = parts[-2]
                    else:
                        filename = 'index.html'
                full_path = os.path.join(self.download_path, filename)
                if os.path.exists(full_path):
                    filename = f"{filename}_{int(time.time())}.tmp"
                    full_path = os.path.join(self.download_path, filename)
                with open(full_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
