import tkinter as tk
from tkinter import scrolledtext
import os
from PIL import Image, ImageTk
import logging
from chat_bubble import ChatBubble  # 导入聊天气泡模块
from info_panel import InfoPanel  # 导入信息面板模块

logger = logging.getLogger(__name__)

class UIBuilder:
    """界面构建类，负责创建和管理用户交互界面组件"""
    def __init__(self, root, screen_width, screen_height):
        """初始化界面构建器"""
        self.root = root
        self.root.title("AgentFromPku - 文本交互")
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 设置根窗口的网格布局
        self.root.grid_rowconfigure(0, weight=4)  # 上半行
        self.root.grid_rowconfigure(1, weight=1)  # 下半行（用于info_frame）
        self.root.grid_columnconfigure(0, weight=2)  # 左侧占2/3
        self.root.grid_columnconfigure(1, weight=1)  # 右侧占1/3
        
        # 界面组件引用
        self.main_frame = None  # 主框架（左侧）
        self.dialog_frame = None  # 右侧对话框框架
        self.toolbar = None
        self.title_label = None
        self.tool_frame = None
        self.input_frame = None
        self.param_frame = None
        self.file_frame = None
        self.button_frame = None
        self.response_frame = None
        self.status_bar = None
        
        # 信息面板
        self.info_panel = None
        
        # 界面元素变量
        self.tool_var = tk.StringVar(value="自动分类")
        self.input_text = None
        self.response_text = None
        self.file_display = None
        self.send_button = None
        self.clear_button = None
        self.upload_button = None
        self.stream_status = None
        
        # 背景图片相关
        self.bg_photo = None
        self.bg_label = None
        self.original_bg_image = None

        # 初始化界面
        self._setup_background()
        self._create_widgets()

        # 设置框架最小尺寸（确保权重计算生效）
        self.root.minsize(800, 600)

        self._setup_layout()
        self._update_param_widgets()
        self.chat_messages = {}  # 存储聊天消息的字典

        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self._on_resize)
        
        # 初始化聊天气泡管理器
        self.chat_bubble = ChatBubble(self)
    
    def set_background(self, image_path):
        """设置新的背景图片"""
        try:
            # 加载新背景图片
            self.original_bg_image = Image.open(image_path)
            
            # 使用当前窗口尺寸
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # 如果窗口尺寸无效，使用屏幕尺寸
            if width < 10 or height < 10:
                width = self.screen_width
                height = self.screen_height
                
            # 调整图片大小
            bg_image = self.original_bg_image.resize((width, height), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            
            # 更新背景标签
            self.bg_label.config(image=self.bg_photo)
            self.bg_label.image = self.bg_photo  # 保持引用
            
            logger.info(f"背景已切换到: {image_path}")
            
        except Exception as e:
            logger.error(f"设置背景失败: {e}")
            # 设置默认背景色
            self.root.config(bg="#f0f0f0")

    def _setup_background(self):
        """设置界面背景图片"""
        try:
            # 尝试加载背景图片
            self.original_bg_image = Image.open("background.jpg")  # 替换为你的图片路径
            bg_image = self.original_bg_image.resize((self.screen_width, self.screen_height), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            self.bg_label = tk.Label(self.root, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            logger.error(f"加载背景图片失败: {e}")
    
    def _create_widgets(self):
        """创建界面组件"""
        # 创建信息面板
        self.info_panel = InfoPanel(self.root)
        
        # 创建右侧对话框框架
        self.dialog_frame = tk.Frame(self.root, bg="#f5e8d9")
        self.dialog_frame.config(highlightbackground="#d4b48c", highlightthickness=7)
        
        # 顶部工具栏
        self.toolbar = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.new_chat_button = tk.Button(
            self.toolbar, text="新会话", font=("SimHei", 10),
            bg="#f5e8d9", fg="#333", padx=5, pady=5,
            relief=tk.FLAT, cursor="hand2"
        )
        self.stream_status = tk.Label(
            self.toolbar, text="流式传输: 就绪", font=("SimHei", 10),
            bg="#f5e8d9", fg="#333"
        )
        self.exit_button = tk.Button(
            self.toolbar, text="退出", command=self.root.destroy,
            font=("SimHei", 10), bg="#f5e8d9", fg="#333",
            padx=10, pady=5, relief=tk.FLAT, cursor="hand2"
        )
        
        # 标题标签
        self.title_label = tk.Label(
            self.dialog_frame, text="AgentFromPku交互界面",
            font=("SimHei", 14, "bold"), bg="#f5e8d9", fg="#333"
        )
        
        # 工具选择框架
        self.tool_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.tool_label = tk.Label(
            self.tool_frame, text="选择工具:", font=("SimHei", 11), bg="#f5e8d9"
        )
        self.tool_combobox = tk.OptionMenu(self.tool_frame, self.tool_var, "自动分类")
        self.tool_combobox.config(font=("SimHei", 11), width=12)
        
        # 输入框架
        self.input_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.input_label = tk.Label(
            self.input_frame, text="输入文本:", font=("SimHei", 11), bg="#f5e8d9"
        )
        self.input_text = scrolledtext.ScrolledText(
            self.input_frame, height=3, font=("SimHei", 11),
            wrap=tk.WORD, bd=1, relief=tk.SOLID, padx=5, pady=5, bg="#fff9f0"
        )
        
        # 参数框架
        self.param_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9",
                                   bd=1, relief=tk.SUNKEN)
        self.param_label = tk.Label(
            self.param_frame, text="工具参数", font=("SimHei", 11), bg="#f5e8d9"
        )
        self.param_widgets = {}  # 存储工具参数输入控件
        
        # 文件框架
        self.file_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.file_label = tk.Label(
            self.file_frame, text="已上传文件:", font=("SimHei", 11), bg="#f5e8d9"
        )
        self.file_display = tk.Label(
            self.file_frame, text="无文件上传（此功能暂不可用）", font=("SimHei", 10),
            bg="#fff9f0", wraplength=400
        )
        
        # 按钮框架
        self.button_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.send_button = tk.Button(
            self.button_frame, text="发送", font=("SimHei", 11),
            bg="#9F8A5A", fg="white", padx=10, pady=3,
            relief=tk.FLAT, cursor="hand2"
        )
        self.clear_button = tk.Button(
            self.button_frame, text="清除", font=("SimHei", 11),
            bg="#f5e8d9", fg="#333", padx=10, pady=3,
            relief=tk.FLAT, cursor="hand2"
        )
        self.upload_button = tk.Button(
            self.button_frame, text="上传文件", font=("SimHei", 11),
            bg="#f5e8d9", fg="#333", padx=10, pady=3,
            relief=tk.FLAT, cursor="hand2"
        )
        
        # 响应框架
        self.response_frame = tk.Frame(self.dialog_frame, bg="#f5e8d9")
        self.response_label = tk.Label(
            self.response_frame, text="", font=("SimHei", 11), bg="#f5e8d9"
        )

        # 创建聊天消息容器
        self.chat_container = tk.Canvas(self.response_frame, bg="#f0f0f0", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.response_frame, orient="vertical", command=self.chat_container.yview)
        self.chat_frame = tk.Frame(self.chat_container, bg="#f0f0f0")
        self.chat_container_window = self.chat_container.create_window((0, 0), window=self.chat_frame, anchor="nw")

        # 配置滚动区域（由ChatBubble类管理）
        self.chat_container.config(yscrollcommand=self.scrollbar.set)
        
        # 状态栏
        self.status_bar = tk.Label(
            self.dialog_frame, text="就绪", bd=1, relief=tk.SUNKEN,
            anchor=tk.W, font=("SimHei", 10), bg="#e0d0c0"
        )
        
        # 绑定工具选择变化事件
        self.tool_var.trace_add("write", self._update_param_widgets)
    
    def _setup_layout(self):
        """设置界面布局"""
        # 设置根窗口的行权重比例 (2:1 = 上半部分:下半部分)
        self.root.grid_rowconfigure(0, weight=4)  # 上半部分占2/3
        self.root.grid_rowconfigure(1, weight=1)  # 下半部分占1/3

        # 配置根窗口的列权重
        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)

        # 放置info_frame和dialog_frame
        self.info_panel.get_frame().grid(row=1, column=0, sticky="nsew", padx=7, pady=7)
        self.dialog_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=7, pady=7)
        
        # 布局对话框内部组件
        self.toolbar.pack(fill=tk.X, padx=10, pady=5)
        self.new_chat_button.pack(side=tk.LEFT, padx=5)
        self.stream_status.pack(side=tk.RIGHT, padx=5)
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        self.title_label.pack(pady=8)
        self.tool_frame.pack(fill=tk.X, padx=15, pady=3)
        self.tool_label.pack(side=tk.LEFT, padx=5)
        self.tool_combobox.pack(side=tk.LEFT, padx=5)
        
        self.response_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=3)
        self.response_label.pack(anchor=tk.W, padx=5)
        
        # 聊天容器布局
        self.chat_container.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y")

        self.file_frame.pack(fill=tk.X, padx=15, pady=3)
        self.file_label.pack(anchor=tk.W, padx=5)
        self.file_display.pack(fill=tk.X, padx=5, pady=3)
        
        self.param_frame.pack(fill=tk.X, padx=15, pady=3)
        self.param_label.pack(anchor=tk.W, padx=5, pady=3)
        
        self.input_frame.pack(fill=tk.X, padx=15, pady=3)
        self.input_label.pack(anchor=tk.W, padx=5)
        self.input_text.pack(fill=tk.X, expand=True, padx=5, pady=3)
        
        self.button_frame.pack(fill=tk.X, padx=15, pady=3)
        self.send_button.pack(side=tk.LEFT, padx=5)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 按钮悬停效果
        self.send_button.bind("<Enter>", lambda e: self.send_button.config(bg="#908E78"))
        self.send_button.bind("<Leave>", lambda e: self.send_button.config(bg="#9F8A5A"))
        self.clear_button.bind("<Enter>", lambda e: self.clear_button.config(bg="#e0d0c0"))
        self.clear_button.bind("<Leave>", lambda e: self.clear_button.config(bg="#f5e8d9"))
        self.upload_button.bind("<Enter>", lambda e: self.upload_button.config(bg="#e0d0c0"))
        self.upload_button.bind("<Leave>", lambda e: self.upload_button.config(bg="#f5e8d9"))
    
    def _on_resize(self, event):
        """处理窗口大小变化事件"""
        if event.widget == self.root:
            total_width = event.width
            total_height = event.height
            self.root.grid_columnconfigure(0, minsize=total_width*2//3)
            self.root.grid_columnconfigure(1, minsize=total_width//3)

            # 更新背景图片
            try:
                if self.original_bg_image:
                    width = event.width
                    height = event.height
                    bg_image = self.original_bg_image.resize((width, height), Image.LANCZOS)
                    self.bg_photo = ImageTk.PhotoImage(bg_image)
                    self.bg_label.config(image=self.bg_photo)
            except Exception as e:
                logger.error(f"调整背景图片失败: {e}")
            
            # 更新信息面板中的照片
            self.info_panel.on_resize()

    def _update_param_widgets(self, *args):
        """更新工具参数输入控件"""
        # 先移除所有现有参数控件
        for widget in self.param_widgets.values():
            widget[0].pack_forget()
        self.param_widgets = {}

        selected_tool = self.tool_var.get()
        if selected_tool == "自动分类":
            return

        # 这里需要在实际使用中由AgentGUI类提供tools属性
        tools = getattr(self, 'tools', {})
        tool_name = None
        for name, tool in tools.items():
            if tool["label"] == selected_tool:
                tool_name = name
                break

        if not tool_name:
            return

        tool_params = tools[tool_name]["params"]
        default_params = tools[tool_name]["default_params"]

        # 为每个参数创建对应的输入控件
        for param_name, param_info in tool_params.items():
            frame = tk.Frame(self.param_frame, bg="#f5e8d9")
            label = tk.Label(
                frame, text=f"{param_info['label']}{' *' if param_info['required'] else ''}:",
                font=("SimHei", 10), bg="#f5e8d9"
            )
            label.pack(side=tk.LEFT, padx=(0, 10))

            if param_info["type"] == "string":
                entry = tk.Entry(frame, width=30, font=("SimHei", 10))
                entry.insert(0, default_params.get(param_name, param_info.get("default", "")))
                entry.pack(side=tk.LEFT)
                self.param_widgets[param_name] = (frame, entry)

            elif param_info["type"] == "number":
                entry = tk.Entry(frame, width=30, font=("SimHei", 10))
                entry.insert(0, str(default_params.get(param_name, param_info.get("default", ""))))
                entry.pack(side=tk.LEFT)
                self.param_widgets[param_name] = (frame, entry)

            elif param_info["type"] == "select" and param_info["options"]:
                var = tk.StringVar(value=default_params.get(param_name, param_info.get("default", "")))
                option_menu = tk.OptionMenu(frame, var, *param_info["options"])
                option_menu.config(font=("SimHei", 10), width=25)
                option_menu.pack(side=tk.LEFT)
                self.param_widgets[param_name] = (frame, var)

            frame.pack(fill=tk.X, padx=5, pady=2)
    
    def update_tool_options(self, tool_options):
        """更新工具选项下拉菜单"""
        menu = self.tool_combobox['menu']
        menu.delete(0, 'end')
        for option in tool_options:
            menu.add_command(label=option, command=lambda value=option: self.tool_var.set(value))
        if tool_options:
            self.tool_var.set(tool_options[0])
    
    def add_photo(self, photo_path):
        """添加人物照片"""
        self.info_panel.add_photo(photo_path)
    
    def set_name(self, name):
        """设置人物姓名"""
        self.info_panel.set_name(name)
    
    def set_intro(self, intro):
        """设置人物介绍信息"""
        self.info_panel.set_intro(intro)

    def add_chat_message(self, message, is_user=True):
        """添加聊天消息气泡（委托给ChatBubble类处理）"""
        return self.chat_bubble.add_chat_message(message, is_user)
    
    def update_chat_message(self, message_widget, new_text):
        """更新现有的聊天消息内容"""
        if isinstance(message_widget, tk.Label):
            message_widget.config(text=new_text)

# 以下是测试代码
if __name__ == "__main__":
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    ui_builder = UIBuilder(root, screen_width, screen_height)
    
    # 示例：添加照片（需替换为实际照片路径）
    ui_builder.add_photo("bk1.jpg")
    
    # 示例：设置人物姓名
    ui_builder.set_name("张三")
    
    # 示例：设置人物介绍信息
    ui_builder.set_intro("这是张三的介绍信息。这是一个测试人物介绍，用于展示UI布局效果。")
    
    # 示例：添加聊天消息
    ui_builder.add_chat_message("你好，这是用户消息", is_user=True)
    ui_builder.add_chat_message("您好，这是AI回复", is_user=False)
    
    root.mainloop()