import tkinter as tk
from PIL import Image, ImageTk
import logging
import time  # 新增导入

logger = logging.getLogger(__name__)

class ChatBubble:
    """聊天气泡管理器，负责创建和管理聊天消息气泡"""
    def __init__(self, ui_builder):
        """初始化聊天气泡管理器"""
        self.ui_builder = ui_builder
        self.root = ui_builder.root
        self.chat_frame = ui_builder.chat_frame
        self.chat_container = ui_builder.chat_container
        self.can_scroll_up = False  # 初始状态下不允许上滑
        self.last_log_time = 0  # 记录最后日志输出时间
        self.welcome_shown = False  # 新增标志变量，确保欢迎消息只显示一次

        # 绑定滚动区域更新事件
        self.chat_frame.bind("<Configure>", self._on_chat_frame_configure)

        # 绑定鼠标滚轮事件（只在聊天容器内生效）
        self.chat_container.bind("<Enter>", self._bind_mousewheel)
        self.chat_container.bind("<Leave>", self._unbind_mousewheel)

        # 确保UI完全加载后再添加欢迎消息
        self.root.bind("<Map>", lambda e: self._on_window_shown())

    def _on_window_shown(self):
        """窗口显示后添加欢迎消息（只执行一次）"""
        if not self.welcome_shown:  # 检查是否已经显示过欢迎消息
            self.root.after(100, self._add_default_welcome_message)
            self.welcome_shown = True  # 标记为已显示

    def _on_chat_frame_configure(self, event):
        """更新聊天容器的滚动区域"""
        self.chat_container.configure(scrollregion=self.chat_container.bbox("all"))
        self._check_scrollability()

    def _bind_mousewheel(self, event):
        """当鼠标进入聊天区域时绑定滚轮事件"""
        self.chat_container.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """当鼠标离开聊天区域时解绑滚轮事件"""
        self.chat_container.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        # 检查是否可以向上滚动
        if event.delta > 0 and not self.can_scroll_up:
            return  # 不允许上滑
        
        self.chat_container.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _check_scrollability(self):
        """检查是否可以滚动（内容是否超出可视区域）"""
        # 获取内容高度和容器高度
        content_height = self.chat_frame.winfo_height()
        container_height = self.chat_container.winfo_height()
        
        # 如果内容高度小于等于容器高度，则不允许上滑
        self.can_scroll_up = content_height > container_height
        
        # 限制日志输出频率（每秒最多一次）
        current_time = time.time()
        if current_time - self.last_log_time > 1.0:
            logger.debug(f"可滚动状态检查 - 内容高度: {content_height}px, 容器高度: {container_height}px, 可上滑: {self.can_scroll_up}")
            self.last_log_time = current_time

    def _add_default_welcome_message(self):
        """添加默认欢迎消息"""
        # 确保容器宽度已经初始化
        self.root.update_idletasks()
        welcome_message = "（欢快地转了个圈，闪亮登场✨）\n“哇！你终于来啦！我是你的向导小精灵派蒙~欢迎来到‘北大时空漫游’！\n在这里，你可以参访燕南园，去勺园欣赏风景，或者到未名湖边遇见更多有趣的灵魂！想去哪儿？随时告诉派蒙就好啦，我嗖的一下就能带你穿越~（骄傲叉腰）\n对了对了，每个地方都藏着惊喜哦！（突然压低声音，神秘兮兮）\n所以——今天想先去哪儿探险呀？燕南园、勺园、还是未名湖边？\n（P.S. 迷路了就大喊三声‘派蒙最好看’，本向导立刻闪现！……喂，最后这句不用当真啦！直接告诉派蒙你想去哪里就可以啦。如果你愿意~还可以看到听到派蒙的声音，看到派蒙的画哦）"
        self.add_chat_message(welcome_message, is_user=False)

    def _calculate_max_width(self):
        """计算气泡的最大允许宽度"""
        # 获取聊天容器的当前宽度
        container_width = self.chat_container.winfo_width()
        
        # 计算最大宽度（减去头像、边距等空间）
        max_width = container_width - 80  
        
        # 确保最小宽度（防止窗口太小时气泡太小）
        return max(max_width, 200)

    def add_chat_message(self, message, is_user=True):
        """添加聊天消息气泡"""
        # 创建气泡框架
        bubble_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
        bubble_frame.pack(fill="x", pady=5)

        # 计算气泡的最大宽度
        max_width = self._calculate_max_width()

        # 用户消息靠右显示
        if is_user:
            # 主容器框架（靠右）
            user_frame = tk.Frame(bubble_frame, bg="#f0f0f0")
            user_frame.pack(side="right", anchor="e")

            # 消息气泡（右侧内部靠左）
            bubble_bg = "#dcf8c6"  # 用户消息背景色
            bubble = tk.Label(
                user_frame, 
                text=message,
                justify="left",
                bg=bubble_bg, 
                padx=10, 
                pady=8,
                font=("SimHei", 11),
                wraplength=max_width
            )
            bubble.pack(side="left", padx=5)

            # 用户头像
            avatar_label = tk.Label(
                user_frame, 
                text="👤",
                font=("Arial", 16), 
                bg="#f0f0f0"
            )
            avatar_label.pack(side="right", padx=5, pady=(3,0), anchor="n")

        # AI回复靠左显示
        else:
            # 主容器框架（靠左）
            ai_frame = tk.Frame(bubble_frame, bg="#f0f0f0")
            ai_frame.pack(side="left", anchor="w")

            # AI头像
            avatar_label = tk.Label(
                ai_frame, 
                text="🤖",
                font=("Arial", 16), 
                bg="#f0f0f0"
            )
            avatar_label.pack(side="left", padx=5, pady=(3,0), anchor="n")

            # 消息气泡（左侧内部靠右）
            bubble_bg = "#ffffff"  # AI消息背景色
            bubble = tk.Label(
                ai_frame, 
                text=message,
                wraplength=max_width, 
                justify="left",
                bg=bubble_bg, 
                padx=10, 
                pady=8,
                font=("SimHei", 11)
            )
            bubble.pack(side="left", padx=5)

        # 自动滚动到底部
        self.chat_frame.update_idletasks()
        self.chat_container.yview_moveto(1.0)
        
        # 检查是否可以滚动
        self._check_scrollability()
        return bubble
