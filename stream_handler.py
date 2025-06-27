import time
import threading
import logging
import os
import tkinter as tk
from tkinter import messagebox
import ctypes
from scene_switcher import switch_scene
from ui_builder import UIBuilder

logger = logging.getLogger(__name__)

class StreamHandler:
    def __init__(self, api_client, ui_builder):
        """初始化流式处理类，绑定API客户端和UI构建器"""
        self.api_client = api_client
        self.ui_builder = ui_builder
        self.request_queue = []
        self.current_request_id = 0
        self.user_id = "user_" + str(int(time.time()))
        self.conversation_id = None
        self.uploaded_files = []
        self.is_streaming = False
        self.last_response_content = None
        self.last_stream_data = ""
        self.is_processing_chunk = False
        self.audio_buttons = {}
        self.image_widgets = {}
        self.output_to_stdout = False
        self.current_response_buffer = ""  # 存储完整的响应内容
        self.current_bubble = None  # 当前聊天气泡的引用
        
        # 绑定UI事件处理
        self.ui_builder.send_button.config(command=self._enqueue_request)
        self.ui_builder.clear_button.config(command=self._clear_all)
        self.ui_builder.upload_button.config(command=self._upload_file)
        self.ui_builder.new_chat_button.config(command=self._new_conversation)
        self.root = self.ui_builder.root
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """窗口关闭时的处理函数"""
        self.root.destroy()
    
    def _enqueue_request(self):
        """将用户请求加入队列，准备发送到API"""
        input_text = self.ui_builder.input_text.get("1.0", tk.END).strip()
        if not input_text:
            messagebox.showwarning("警告", "请输入文本内容")
            return

        # 添加用户消息
        self._add_user_input_to_response(input_text)
        
        # 清空输入栏
        self.ui_builder.input_text.delete("1.0", tk.END)

        self.ui_builder.status_bar.config(text="请求处理中...")
        self.ui_builder.send_button.config(state=tk.DISABLED)
        self.ui_builder.stream_status.config(text="流式传输: 进行中", fg="blue")
        self.is_streaming = True
        self.output_to_stdout = False

        self.current_request_id += 1
        request_id = self.current_request_id
        selected_tool = self.ui_builder.tool_var.get()
        tool_name = None

        if selected_tool != "自动分类":
            for name, tool in self.api_client.tools.items():
                if tool["label"] == selected_tool:
                    tool_name = name
                    break

        tool_params = self._get_param_values()

        files = self.uploaded_files.copy()
        self.uploaded_files = []

        # 将请求添加到队列
        self.request_queue.append(
            (request_id, input_text, tool_name, tool_params, files)
        )

        # 如果是队列中的第一个请求，启动处理线程
        if len(self.request_queue) == 1:
            threading.Thread(target=self._process_request_queue, daemon=True).start()
    
    def _process_request_queue(self):
        """处理请求队列，支持流式响应实时更新"""
        while self.request_queue:
            request_id, input_text, tool_name, tool_params, files = self.request_queue[0]

            # 调用API客户端发送请求，设置流式响应回调函数
            self.api_client.call_agent(
                input_text,
                tool_name,
                tool_params,
                self.user_id,
                files,
                on_data=lambda data: self.root.after(
                    0, self._handle_stream_data, data, request_id
                ),
                on_end=lambda response: self.root.after(
                    0, self._handle_stream_end, response, request_id
                ),
            )

            # 等待流式响应完成，超时时间120秒
            timeout = 0
            while self.is_streaming and timeout < 120:
                time.sleep(0.5)
                timeout += 0.5

            # 处理完当前请求后从队列中移除
            self.request_queue.pop(0)

            # 如果队列中还有请求，等待0.5秒后继续处理
            if self.request_queue:
                time.sleep(0.5)
            else:
                self.root.after(0, self._request_complete)
    
    def _handle_stream_data(self, data, request_id):
        """处理流式数据更新，将数据实时显示到界面"""
        if request_id != self.current_request_id:
            return

        # 处理音频和图片检测事件
        if data["type"] == "audio_detected":
            self.output_to_stdout = True
            print("[音频响应] 检测到音频内容，已切换到标准输出")
            print(data["content"], end="", flush=True)
            return

        if data["type"] == "image_detected":
            self.output_to_stdout = True
            print("[图片响应] 检测到图片内容，已切换到标准输出")
            print(data["content"], end="", flush=True)
            return

                # 处理文本片段
        if data["type"] == "text":
            chunk_content = data.get("content", "")
            
            # 追加到缓冲区
            self.current_response_buffer += chunk_content
            
            # 更新聊天气泡
            if not self.current_bubble:
                # 创建新气泡
                self.current_bubble = self.ui_builder.add_chat_message(
                    self.current_response_buffer, 
                    is_user=False
                )
            else:
                # 更新现有气泡内容
                self.ui_builder.update_chat_message(
                    self.current_bubble, 
                    self.current_response_buffer
                )
                
            # 确保气泡滚动到底部
            self.ui_builder.chat_container.yview_moveto(1.0)
                
            self.is_processing_chunk = False
    
    def _handle_stream_end(self, response, request_id):
        """处理流式响应结束，处理最终响应内容"""
        if request_id != self.current_request_id:
            return

        # 处理音频文件路径
        if response.get("audio_file_path"):
            # 添加音频消息
            self._add_audio_message(response["audio_file_path"], response.get("original_content", ""))
        
        # 处理图片文件路径
        elif response.get("image_file_path"):
            self._add_image_message(response["image_file_path"], response.get("original_content", ""))
        
        # 更新会话 ID
        if response.get("conversation_id"):
            self.conversation_id = response["conversation_id"]
        
        # 重置气泡引用
        if hasattr(self, 'current_bubble'):
            self.current_bubble = None 
        
        # 更新界面状态
        self.is_streaming = False
        self.ui_builder.stream_status.config(text="流式传输: 就绪", fg="#333")
        
        # 清空缓冲区
        self.current_response_buffer = ""
        self._request_complete()
        
        # 调用场景切换 - 使用修改后的参数顺序
        original_content = response.get("original_content", "")
        if original_content and "*切换地点*" in original_content:
            switch_scene(
                original_content=original_content,
                ui_builder=self.ui_builder,
                api_client=self.api_client
            )
        
    def _request_complete(self):
        """请求处理完成，更新界面状态"""
        self.ui_builder.status_bar.config(text="就绪")
        self.ui_builder.send_button.config(state=tk.NORMAL)
    
    def _add_user_input_to_response(self, input_text):
        """添加用户消息（右侧气泡）"""
        self.ui_builder.add_chat_message(input_text, is_user=True)
    
    def _clear_all(self):
        """清除所有内容，包括输入、响应、上传文件等"""
        # 清除输入框内容
        self.ui_builder.input_text.delete("1.0", tk.END)
        # 清空上传文件列表
        self.uploaded_files = []
        # 更新状态栏文本为就绪
        self.ui_builder.status_bar.config(text="就绪")
        # 清空音频按钮状态记录
        self.audio_buttons = {}
    # 清空图片控件记录
        self.image_widgets = {}
    # 重置输出到标准输出的标志
        self.output_to_stdout = False

    # 清除聊天框内容
        for widget in self.ui_builder.chat_frame.winfo_children():
            widget.destroy()

    # 停止所有正在播放的音频
        for state in self.audio_buttons.values():
            if state["is_playing"]:
                self.api_client._stop_file(state["file_path"])

    # 这里不重置与流式响应相关的状态
        self.last_response_content = None
        self.last_stream_data = ""
        self.is_processing_chunk = False
    def _new_conversation(self):
        """创建新会话，重置会话状态"""
        # 重置会话 ID
        self.api_client.current_conversation_id = None
        self.conversation_id = None

        # 清除所有内容，包括输入、响应、上传文件等
        self._clear_all()


        self.ui_builder.set_background("background.jpg")
        self.ui_builder.add_photo("pm.jpg")  # 设置默认照片
        self.ui_builder.set_name("派蒙")  # 设置姓名
        self.ui_builder.set_intro("    派蒙是旅行者在提瓦特的旅途中钓到的奇妙生物，同时也是旅行者的向导与引路人。\n    年幼的小女孩外形，白色齐肩发，戴着一颗黑曜石打造的星星发饰，头顶悬浮王冠（派蒙待机动作可以看到有取下来的动作）背后的小披风有着星空纹理般的黑蓝色，披风有类似星座纹路的装饰，飘动起来似乎可以看到星辰在闪动，眼睛远处看是蓝瞳，拉近视角后也可以看见眼中的星辰，衣着镶金边的白色连衣裤，衣服中央有类似摩拉货币的图案，脚穿白镶金的靴子，身边飘动着闪闪星座纹路，派蒙贪吃爱财，也是个话痨，因为旅行者很多台词都被派蒙抢了，所以显得她话有些多。\n    派蒙非常珍视与旅行者的友谊，屡次强调自己是“最好的伙伴”，不会和旅行者分开。")  # 设置介绍

    # 更新状态栏
        self.ui_builder.status_bar.config(text="新会话已创建")

    # 重置流式处理相关状态
        self.last_response_content = None
        self.last_stream_data = ""
        self.is_processing_chunk = False

    # 重置当前响应缓冲区和当前聊天气泡引用
        self.current_response_buffer = ""
        self.current_bubble = None

    # 重置输出到标准输出的标志
        self.output_to_stdout = False

    # 重新添加欢迎消息
        self.ui_builder.chat_bubble._add_default_welcome_message()

    # 确保聊天区域滚动到底部
        self.ui_builder.chat_container.yview_moveto(1.0)

    
    def _upload_file(self):
        """上传文件到Dify API"""
        try:
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("所有支持文件", "*.txt *.md *.pdf"),
                    ("所有文件", "*.*"),
                ]
            )
            if not file_path:
                return

            self.ui_builder.status_bar.config(text="文件上传中...")
            self.ui_builder.upload_button.config(state=tk.DISABLED)

            file_info = self.api_client.upload_file(file_path)
            if file_info:
                self.uploaded_files.append(file_info)
                file_name = os.path.basename(file_path)
                self.ui_builder.file_display.config(text=f"已上传文件: {file_name}")
                messagebox.showinfo("成功", f"文件 {file_name} 上传成功")
            else:
                messagebox.showerror("错误", "文件上传失败")

        except Exception as e:
            logger.error("文件上传异常: %s", e)
        finally:
            self.ui_builder.status_bar.config(text="就绪")
            self.ui_builder.upload_button.config(state=tk.NORMAL)
    
    def _add_audio_message(self, file_path, content):
        """在聊天框中添加音频消息"""
        # 创建包含播放按钮的框架
        frame = tk.Frame(self.ui_builder.chat_frame, bg="#f0f0f0")
        frame.pack(fill="x", pady=5)
        
        # 添加AI头像
        avatar_label = tk.Label(frame, text="🤖", font=("Arial", 16), bg="#f0f0f0")
        avatar_label.pack(side="left", padx=5)
        
        # 添加播放按钮
        button = tk.Button(
            frame, 
            text="▶ 播放音频", 
            font=("SimHei", 11),
            bg="#e0f0ff", 
            fg="#0056b3",
            padx=10,
            pady=5,
            relief=tk.RAISED,
            cursor="hand2"
        )
        button.config(command=lambda fp=file_path, btn=button: self._toggle_audio(fp, btn))
        button.pack(side="left", padx=5)
        
        # 记录按钮状态
        self.audio_buttons[button] = {
            "file_path": file_path,
            "is_playing": False
        }
        
        # 滚动到底部
        self.ui_builder.chat_container.yview_moveto(1.0)
    
    def _add_image_message(self, file_path, content):
        """在聊天框中添加图片消息"""
        try:
            from PIL import Image, ImageTk
            # 创建框架
            frame = tk.Frame(self.ui_builder.chat_frame, bg="#f0f0f0")
            frame.pack(fill="x", pady=5)
            
            # 添加AI头像
            avatar_label = tk.Label(frame, text="🤖", font=("Arial", 16), bg="#f0f0f0")
            avatar_label.pack(side="left", padx=5)
            
            # 加载并显示图片缩略图
            img = Image.open(file_path)
            img = img.resize((150, 100), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            image_label = tk.Label(frame, image=photo, bg="#ffffff", cursor="hand2")
            image_label.image = photo
            image_label.pack(side="left", padx=5)
            image_label.bind("<Button-1>", lambda e, fp=file_path: self._show_large_image(fp))
            
            # 记录图片控件
            self.image_widgets[image_label] = {
                "file_path": file_path,
                "photo": photo
            }
            
            # 滚动到底部
            self.ui_builder.chat_container.yview_moveto(1.0)
            
        except Exception as e:
            logger.error(f"添加图片消息失败: {e}")
            self.ui_builder.add_chat_message(f"[图片加载失败: {str(e)}]", is_user=False)
    
    def _show_large_image(self, file_path):
        """显示大图，在新窗口中打开原始尺寸图片"""
        try:
            from PIL import Image, ImageTk
            # 加载原始尺寸图片
            img = Image.open(file_path)
            
            # 创建新窗口显示大图
            large_window = tk.Toplevel(self.root)
            large_window.title("查看大图")
            large_window.geometry(f"{img.width}x{img.height+50}")
            large_window.resizable(True, True)
            
            # 转换为Tkinter可用的图片对象
            photo = ImageTk.PhotoImage(img)
            
            # 创建图片标签
            image_label = tk.Label(large_window, image=photo)
            image_label.image = photo  # 保留引用
            image_label.pack(padx=10, pady=10)
            
            # 创建关闭按钮
            close_btn = tk.Button(large_window, text="× 关闭", command=large_window.destroy,
                                 font=("SimHei", 10), bg="#f0f0f0", fg="#333",
                                 padx=10, pady=5, relief=tk.RAISED, cursor="hand2")
            close_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"显示大图时出错: {str(e)}")
    
    def _toggle_audio(self, file_path, button):
        """切换音频播放/暂停状态"""
        # 获取按钮状态
        button_state = self.audio_buttons.get(button)
        if not button_state:
            return
            
        if button_state["is_playing"]:
            # 当前是播放状态，切换到暂停
            self._pause_audio(file_path, button)
        else:
            # 当前是暂停状态，切换到播放
            self._play_audio(file_path, button)
    
    def _play_audio(self, file_path, button):
        """播放指定路径的音频文件"""
        self.ui_builder.status_bar.config(text="正在播放音频...")
        
        # 先停止所有其他正在播放的音频
        self._stop_all_other_audios(file_path)
        
        # 获取当前播放时间（如果之前有暂停）
        current_time = 0
        if file_path in self.api_client.playing_files and self.api_client.playing_files[file_path]["paused"]:
            current_time = self.api_client.get_playback_time(file_path)
        
        # 更新按钮状态
        button.config(text="■ 暂停", bg="#ffe0e0", fg="#b30000")
        self.audio_buttons[button]["is_playing"] = True
        
        # 播放音频
        result = self.api_client._play_file(file_path, current_time)
        if not result:
            # 播放失败，恢复按钮状态
            button.config(text="▶ 播放音频", bg="#e0f0ff", fg="#0056b3")
            self.audio_buttons[button]["is_playing"] = False
        
        self.root.after(1000, lambda: self.ui_builder.status_bar.config(text="就绪"))
    
    def _pause_audio(self, file_path, button):
        """暂停指定路径的音频文件"""
        self.ui_builder.status_bar.config(text="已暂停音频")
        
        # 暂停播放
        result = self.api_client._pause_file(file_path)
        
        # 更新按钮状态
        if result:
            button.config(text="▶ 继续播放", bg="#e0f0ff", fg="#0056b3")
            self.audio_buttons[button]["is_playing"] = False
        
        self.root.after(1000, lambda: self.ui_builder.status_bar.config(text="就绪"))
    
    def _stop_all_other_audios(self, current_file_path):
        """停止所有其他正在播放的音频"""
        for btn, state in list(self.audio_buttons.items()):
            if state["is_playing"] and state["file_path"] != current_file_path:
                self.api_client._stop_file(state["file_path"])
                btn.config(text="▶ 播放音频", bg="#e0f0ff", fg="#0056b3")
                state["is_playing"] = False
    
    def _get_param_values(self):
        """获取工具参数值，从参数输入控件中提取用户输入"""
        selected_tool = self.ui_builder.tool_var.get()
        if selected_tool == "自动分类":
            return None

        tool_name = None
        for name, tool in self.api_client.tools.items():
            if tool["label"] == selected_tool:
                tool_name = name
                break

        if not tool_name:
            return None

        params = {}
        for param_name, (_, widget) in self.ui_builder.param_widgets.items():
            if isinstance(widget, tk.Entry):
                params[param_name] = widget.get()
            elif isinstance(widget, tk.StringVar):
                params[param_name] = widget.get()
        return params