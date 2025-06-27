import tkinter as tk
import logging
import ctypes
from ui_builder import UIBuilder
from stream_handler import StreamHandler

logger = logging.getLogger(__name__)

# 定义 Windows API 函数，用于控制任务栏显示/隐藏
user32 = ctypes.windll.user32
SW_HIDE = 0
SW_SHOW = 5

def hide_taskbar():
    """隐藏Windows任务栏"""
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    user32.ShowWindow(hwnd, SW_HIDE)

def show_taskbar():
    """显示Windows任务栏"""
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    user32.ShowWindow(hwnd, SW_SHOW)

class AgentGUI:
    """智能体图形用户界面类，整合界面构建和流式处理"""
    def __init__(self, root, api_client, screen_width, screen_height):
        """初始化图形界面，整合UI构建和流式处理"""
        self.root = root
        self.api_client = api_client
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 初始化UI构建器
        self.ui_builder = UIBuilder(root, screen_width, screen_height)
        self.ui_builder.tools = api_client.tools  # 传递工具配置
        
        # 更新工具选项
        tool_options = ["自动分类"]
        if isinstance(api_client.tools, dict):
            for tool in api_client.tools.values():
                tool_options.append(tool["label"])
        self.ui_builder.update_tool_options(tool_options)
        
        # 在初始化流式处理器之前添加以下内容
        self.ui_builder.add_photo("pm.jpg")  # 设置默认照片
        self.ui_builder.set_name("派蒙")  # 设置姓名
        self.ui_builder.set_intro("    派蒙是旅行者在提瓦特的旅途中钓到的奇妙生物，同时也是旅行者的向导与引路人。\n    年幼的小女孩外形，白色齐肩发，戴着一颗黑曜石打造的星星发饰，头顶悬浮王冠（派蒙待机动作可以看到有取下来的动作）背后的小披风有着星空纹理般的黑蓝色，披风有类似星座纹路的装饰，飘动起来似乎可以看到星辰在闪动，眼睛远处看是蓝瞳，拉近视角后也可以看见眼中的星辰，衣着镶金边的白色连衣裤，衣服中央有类似摩拉货币的图案，脚穿白镶金的靴子，身边飘动着闪闪星座纹路，派蒙贪吃爱财，也是个话痨，因为旅行者很多台词都被派蒙抢了，所以显得她话有些多。\n    派蒙非常珍视与旅行者的友谊，屡次强调自己是“最好的伙伴”，不会和旅行者分开。")  # 设置介绍
        # self.ui_builder.set_intro("paimenghsjakhsaksh")
        # 初始化流式处理器
        self.stream_handler = StreamHandler(api_client, self.ui_builder)
        # 在UIBuilder初始化后添加：
        # 增大聊天区域高度（原高度为12行）
        self.ui_builder.response_frame.config(height=20)  # 增加聊天区域高度

    def on_close(self):
        """窗口关闭时的处理函数，销毁主窗口"""
        self.root.destroy()

# 以下是使用示例
if __name__ == "__main__":
    # 这里假设已经有了 api_client 的实例
    class MockAPIClient:
        """模拟API客户端，用于测试GUI界面"""
        def __init__(self):
            self.tools = {}
            self.playing_files = {}

        def call_agent(self, *args, **kwargs):
            pass

        def upload_file(self, *args, **kwargs):
            return {"file_path": "test_file.txt", "file_name": "test.txt"}

        def _play_file(self, file_path, current_time=0):
            self.playing_files[file_path] = {"paused": False}
            return True

        def _pause_file(self, file_path):
            if file_path in self.playing_files:
                self.playing_files[file_path]["paused"] = True
                return True
            return False

        def _stop_file(self, file_path):
            if file_path in self.playing_files:
                del self.playing_files[file_path]
                return True
            return False

        def get_playback_time(self, file_path):
            return 5

    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建应用
    api_client = MockAPIClient()
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    app = AgentGUI(root, api_client, screen_width, screen_height)
    root.mainloop()