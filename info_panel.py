import tkinter as tk
from PIL import Image, ImageTk
import os
import logging

logger = logging.getLogger(__name__)

class InfoPanel:
    """左下角信息面板类，负责显示人物照片、姓名和介绍信息"""
    def __init__(self, parent_frame, bg_color="#f5e8d9", width=600, height=105):
        """初始化信息面板
        Args:
            parent_frame: 父框架
            bg_color: 背景颜色
            width: 固定宽度
            height: 固定高度
        """
        self.parent_frame = parent_frame
        self.bg_color = bg_color
        self.panel_width = width
        self.panel_height = height
        
        # 创建信息面板框架（固定大小）
        self.info_frame = tk.Frame(self.parent_frame, 
                                  bg=self.bg_color,
                                  width=self.panel_width,
                                  height=self.panel_height)
        self.info_frame.config(highlightbackground="#b89b7a", highlightthickness=7)
        self.info_frame.pack_propagate(False)  # 禁止子组件影响框架大小
        self.info_frame.grid_propagate(False)   # 双重确保
        
        # 照片框（固定大小）
        self.photo_frame = tk.Frame(self.info_frame, 
                                   bg=self.bg_color,
                                   width=150,
                                   height=150)
        self.photo_frame.config(highlightbackground="#b89b7a", highlightthickness=0)
        self.photo_frame.pack_propagate(False)
        self.photo_frame.grid_propagate(False)
        
        # 用于显示照片的标签
        self.photo_label = None
        self.photo_path = None
        self.original_photo = None
        
        # 用于显示人物姓名的标签（不再设置固定字符宽度）
        self.name_label = tk.Label(self.info_frame, 
                                  text="", 
                                  font=("SimHei", 14),
                                  bg=self.bg_color, 
                                  fg="#333",
                                  anchor="nw",
                                  wraplength=400)  # 改用换行长度控制
        
        # 用于显示人物介绍信息的标签
        self.intro_label = tk.Label(self.info_frame, 
                                   text="", 
                                   font=("SimHei", 11),
                                   bg=self.bg_color, 
                                   fg="#333", 
                                   wraplength=530,  # 固定换行宽度
                                   anchor="nw",
                                   justify="left")
        
        # 布局照片和个人信息
        self._setup_layout()
    
    def _setup_layout(self):
        """设置信息面板的布局"""
        # 使用pack布局
        self.photo_frame.pack(side="left", padx=20, pady=20, fill="none", expand=False)
        
        # 右侧信息区域
        info_right = tk.Frame(self.info_frame, bg=self.bg_color)
        info_right.pack(side="right", padx=20, pady=20, fill="both", expand=True)
        
        # 姓名和介绍信息布局
        self.name_label.pack(side="top", anchor="nw", pady=(0, 5))
        self.intro_label.pack(side="top", fill="both", expand=True)
    
    def add_photo(self, photo_path):
        """添加人物照片，固定大小显示"""
        try:
            if not os.path.exists(photo_path):
                return
                
            self.photo_path = photo_path
            self.original_photo = Image.open(photo_path)
            
            # 固定照片显示尺寸为140x140（小于框架尺寸）
            resized_photo = self.original_photo.resize((140, 140), Image.LANCZOS)
            photo_img = ImageTk.PhotoImage(resized_photo)
                
            if not self.photo_label:
                self.photo_label = tk.Label(self.photo_frame, 
                                          image=photo_img, 
                                          bg=self.bg_color)
                self.photo_label.pack(anchor="nw")
                self.photo_label.image = photo_img
            else:
                self.photo_label.config(image=photo_img)
                self.photo_label.image = photo_img
                
        except Exception as e:
            logger.error(f"加载照片失败: {e}")

    def set_name(self, name):
        """设置人物姓名"""
        self.name_label.config(text=name)
    
    def set_intro(self, intro):
        """设置人物介绍信息"""
        self.intro_label.config(text=intro)
    
    def get_frame(self):
        """获取信息面板的框架"""
        return self.info_frame
    
    def on_resize(self):
        """处理大小变化事件 - 现在大小固定，不需要处理"""
        pass