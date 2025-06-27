import tkinter as tk
from tkinter import messagebox, simpledialog
import pygame
import os
import json
import sys
from PIL import Image, ImageTk
from gui import AgentGUI
from api_client import AgentAPIClient  # 假设 AgentAPIClient 定义在 api_client.py 中

def load_config():
    """加载 config.json 文件"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("错误：缺少 config.json 文件！请复制 config.example.json 并填写密钥")
        exit(1)

# 全局配置
config = load_config()
API_KEY = config["api_keys"]["default"] 

def main():
    """主程序入口函数，负责初始化程序环境、创建API客户端和GUI界面"""
    # 检查pygame和PIL库是否安装
    try:
        import pygame
        from PIL import Image, ImageTk
    except ImportError:
        messagebox.showerror("依赖缺失", "请先安装pygame和Pillow库: pip install pygame pillow")
        sys.exit(1)

    # 初始化pygame及其音频模块
    pygame.init()
    pygame.mixer.init()

    # 配置API基础URL
    base_url = "https://api.dify.ai/v1"  # Dify API基础地址

    # 获取API密钥，支持硬编码或用户输入
    API_KEY = "app-TcB6dTgLZYYhCm3DDKZwBA8a"  # 请替换为实际API密钥
    # API_KEY = "app-7iOV2ODglkRwDmtw0UG82Xyn"
    if not API_KEY:
        api_key = simpledialog.askstring("API密钥", "请输入Dify API密钥:")
        if not api_key:
            print("未提供API密钥，程序退出")
            pygame.quit()
            sys.exit(1)
    else:
        api_key = API_KEY

    # 确保下载目录存在，用于存储下载的音频和图片文件
    download_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
    if not os.path.exists(download_dir):
        os.makedirs(download_dir, exist_ok=True)

    # 创建API客户端实例，用于与Dify API交互
    api_client = AgentAPIClient(base_url, api_key)


    # 创建主窗口和GUI界面
    root = tk.Tk()
    # 获取屏幕尺寸以实现全屏显示

    # 设置初始窗口大小（可调整）
    initial_width = 1200
    initial_height = 800
    root.geometry(f"{initial_width}x{initial_height}")
    
    # 允许窗口调整大小
    root.resizable(False, False)
    
    # 创建GUI应用实例
    app = AgentGUI(root, api_client, initial_width, initial_height)
    
    # 进入主事件循环
    root.mainloop()

    # 程序退出时清理pygame资源
    pygame.quit()

if __name__ == "__main__":
    main()
