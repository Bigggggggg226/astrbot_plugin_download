from astrbot.api.all import *
import re
import requests
import os
import time

# 注册插件
@register("download_link_with_progress", "Your Name", "Downloads files from links with progress feedback", "1.0.0")
class DownloadLinkWithProgressPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 创建下载目录
        self.download_path = 'downloads/'
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    # 处理消息事件
    def handle_message(self, event):
        message = event.message
        # 使用正则表达式提取 URL
        urls = re.findall(r'https?://\S+', message)
        if not urls:
            self.send_message(event, "未检测到链接，请提供有效的 URL！")
            return
        
        # 对每个检测到的 URL 执行下载
        for url in urls:
            self.send_message(event, f"开始下载: {url}")
            if self.download_file_with_progress(url, event):
                full_path = os.path.join(self.download_path, url.split('/')[-1] or 'index.html')
                self.send_message(event, f"下载完成: {url} 已保存到 {full_path}")
            else:
                self.send_message(event, f"下载失败: {url}")

    # 下载文件并显示进度
    def download_file_with_progress(self, url, event):
        try:
            # 以流式方式请求 URL
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('Content-Length', 0))
            
            # 如果无法获取文件大小，提示用户并继续下载
            if total_size == 0:
                self.send_message(event, f"无法获取 {url} 的文件大小，将直接下载")
            
            # 生成文件名，避免重复
            filename = url.split('/')[-1]
            if not filename:
                filename = 'index.html'
            full_path = os.path.join(self.download_path, filename)
            if os.path.exists(full_path):
                filename = f"{filename}_{int(time.time())}.tmp"
                full_path = os.path.join(self.download_path, filename)

            # 开始下载并写入文件
            downloaded = 0
            chunk_size = 1024  # 每次读取 1KB
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 如果知道总大小，计算并显示进度
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            # 每 10% 更新一次进度，避免频繁发送消息
                            if progress % 10 < 0.1:  # 使用小范围判断
                                self.send_message(event, f"下载 {url}: {progress:.2f}%")
            return True
        except Exception as e:
            self.send_message(event, f"下载 {url} 时出错: {str(e)}")
            return False
