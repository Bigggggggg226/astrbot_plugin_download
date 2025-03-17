from nakuru.entities.components import *
from nakuru import GroupMessage, FriendMessage
from botpy.message import Message, DirectMessage
from cores.qqbot.global_object import AstrMessageEvent
import requests
import re
import os
from urllib.parse import urlparse

class DownloadPlugin:
    def __init__(self):
        self.save_path = "downloads"  # 默认下载目录
        self.allowed_extensions = ['.pdf', '.jpg', '.png']  # 允许下载的文件类型
        os.makedirs(self.save_path, exist_ok=True)

    def run(self, ame: AstrMessageEvent):
        # 检测消息中的链接
        urls = re.findall(r'https?://\S+', ame.message_str)
        
        if urls:
            results = []
            for url in urls:
                try:
                    # 下载文件
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    # 解析文件名
                    parsed = urlparse(url)
                    filename = os.path.basename(parsed.path)
                    if not filename:
                        filename = f"file_{int(time.time())}"
                    
                    # 检查文件类型
                    _, ext = os.path.splitext(filename)
                    if ext.lower() not in self.allowed_extensions:
                        return True, (False, "不支持的文件类型", "download")
                    
                    # 保存文件
                    full_path = os.path.join(self.save_path, filename)
                    with open(full_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                
                    results.append(f"✅ 下载成功：{filename}")
                except Exception as e:
                    results.append(f"❌ 下载失败：{str(e)}")
            
            reply = "\n".join(results)
            return True, (True, reply, "download")
            
        return False, None

    def info(self):
        return {
            "name": "Downloader",
            "desc": "链接自动下载插件",
            "help": "发送包含文件链接的消息即可自动下载\n支持格式：" + ", ".join(self.allowed_extensions),
            "version": "v1.0",
            "author": "AstrBot-Plugin-Author"
        }
