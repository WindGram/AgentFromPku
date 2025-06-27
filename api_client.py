import os
import re
import requests
import json
import tempfile
import subprocess
import threading
import time
from datetime import datetime
import logging
from io import BytesIO
import platform
import pygame  # 用于音频播放控制
from PIL import Image, ImageTk  # 用于图片处理

# 初始化pygame音频模块
pygame.mixer.init()

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="agent_client.log",
)
logger = logging.getLogger(__name__)

# 文件类型映射表，用于确定下载文件的扩展名
CONTENT_TYPE_MAPPING = {
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/mp4": "m4a",
    "application/octet-stream": "bin",
}


class AgentAPIClient:
    """Dify API客户端类，负责与Dify API通信，处理文件上传、音频播放等功能"""
    def __init__(self, base_url, api_key):
        """初始化API客户端，加载配置并设置基本参数"""
        self.base_url = base_url  # API基础URL
        self.api_key = api_key  # API密钥
        self.tools = {}  # 清空工具配置
        self.llm_endpoint = {"model": "deepseek-chat", "provider": "langgenius/deepseek/deepseek"}  # 默认LLM端点配置
        self.chat_endpoint = "/chat-messages"  # 聊天消息端点
        self.timeout = 120  # 请求超时时间(秒)
        self.current_conversation_id = None  # 当前会话ID
        self.files = []  # 上传文件列表
        self.playing_files = {}  # 存储正在播放的文件及其状态
        self.audio_playback_completed = threading.Event()  # 音频播放完成事件
        self.image_cache = {}  # 缓存下载的图片
        self.download_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
        # 确保下载目录存在
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, exist_ok=True)

    def upload_file(self, file_path, file_type="document"):
        """上传文件到Dify API，返回文件信息"""
        if not os.path.exists(file_path):
            logger.error("文件不存在: %s", file_path)
            return None

        try:
            upload_url = f"{self.base_url}/files/upload"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            file_ext = os.path.splitext(file_path)[1].lstrip(".").upper()
            file_types = {
                "document": [
                    "TXT",
                    "MD",
                    "MARKDOWN",
                    "PDF",
                    "HTML",
                    "XLSX",
                    "XLS",
                    "DOCX",
                    "CSV",
                    "EML",
                    "MSG",
                    "PPTX",
                    "PPT",
                    "XML",
                    "EPUB",
                ],
            }

            # 确定文件类型
            if file_ext not in sum(file_types.values(), []):
                file_type = "custom"

            # 读取文件并发送上传请求
            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        f,
                        f"application/{file_ext.lower()}",
                    )
                }
                data = {"user": "default_user"}

                response = requests.post(
                    upload_url, files=files, data=data, headers=headers, timeout=30
                )
                response.raise_for_status()

                file_data = response.json()
                logger.info("文件上传成功，ID: %s", file_data.get("id"))
                return {
                    "type": file_type,
                    "transfer_method": "local_file",
                    "upload_file_id": file_data.get("id"),
                }

        except requests.exceptions.RequestException as e:
            logger.error("文件上传失败: %s", e)
            if response and response.status_code == 400:
                error_msg = response.json().get("message", "参数错误")
            else:
                error_msg = f"文件上传失败: {str(e)}"
            logger.error(error_msg)
            return None

    def call_agent(
        self,
        input_text,
        tool_name=None,
        tool_params=None,
        user_id="default_user",
        files=None,
        on_data=None,
        on_end=None,
    ):
        """调用Dify智能体API，支持会话持久化和流式响应"""
        request_body = {
            "query": input_text,
            "user": user_id,
            "response_mode": "streaming",
            "inputs": {},
            "auto_generate_name": True,
        }

        # 设置会话ID以保持上下文
        if self.current_conversation_id:
            request_body["conversation_id"] = self.current_conversation_id

        # 添加上传文件
        if files:
            request_body["files"] = files

        # 设置工具调用参数
        if tool_name and tool_name in self.tools:
            tool = self.tools[tool_name]
            params = tool_params or tool["default_params"]
            request_body["llm_only"] = False
            request_body["tools"] = [{"name": tool_name, "parameters": params}]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            url = f"{self.base_url}{self.chat_endpoint}"
            logger.info("发送API请求，URL：%s，请求体：%s", url, request_body)

            # 发送POST请求，设置流式响应
            response = requests.post(
                url,
                json=request_body,
                headers=headers,
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()

            return self._process_stream_response(response, on_data, on_end)

        except requests.exceptions.HTTPError as e:
            error_data = response.json() if response.content else {"message": str(e)}
            error_msg = f"HTTP错误 {e.response.status_code}: {error_data.get('message', '未知错误')}"
            logger.error(error_msg)
            if on_end:
                on_end({"type": "text", "content": error_msg})
            return {"type": "text", "content": error_msg}
        except requests.exceptions.RequestException as e:
            logger.error("API请求失败: %s", e)
            if on_end:
                on_end({"type": "text", "content": f"API请求失败: {str(e)}"})
            return {"type": "text", "content": f"API请求失败: {str(e)}"}
        except Exception as e:
            logger.error("处理请求时发生异常: %s", e)
            if on_end:
                on_end({"type": "text", "content": f"处理请求异常: {str(e)}"})
            return {"type": "text", "content": f"处理请求异常: {str(e)}"}

    def _process_stream_response(self, response, on_data, on_end):
        """处理流式响应，解析SSE事件并实时回调"""
        messages = []
        conversation_id = None
        task_id = None
        is_complete = False
        full_response = ""
        is_streaming = False  # 标记是否为流式响应
        audio_file_path = None  # 存储音频文件路径
        image_file_path = None  # 存储图片文件路径
        audio_detected = False  # 标记是否检测到音频
        image_detected = False  # 标记是否检测到图片
        original_content = ""  # 存储原始内容

        # 逐行处理流式响应
        for line in response.iter_lines():
            if line:
                try:
                    data_line = line.decode("utf-8")
                    if data_line.startswith("data: "):
                        event_data = json.loads(data_line[6:])
                        event_type = event_data.get("event")

                        task_id = event_data.get("task_id")
                        is_streaming = True  # 确认是流式响应

                        if event_type == "message":
                            message_chunk = event_data.get("answer", "")
                            messages.append(message_chunk)
                            full_response += message_chunk
                            original_content += message_chunk  # 保存原始内容

                            # 检测响应中的音频或图片标记
                            if "[音频]" in message_chunk and not audio_detected and not image_detected:
                                audio_detected = True
                                # 立即通知UI切换到标准输出
                                if on_data:
                                    on_data({"type": "audio_detected", "content": message_chunk})
                            elif "[图片]" in message_chunk and not image_detected and not audio_detected:
                                image_detected = True
                                # 立即通知UI切换到标准输出
                                if on_data:
                                    on_data({"type": "image_detected", "content": message_chunk})

                            # 通知UI更新流式响应内容
                            if on_data and not audio_detected and not image_detected:
                                on_data(
                                    {
                                        "type": "text",
                                        "content": message_chunk,
                                        "is_chunk": True,
                                    }
                                )

                        elif event_type == "error":
                            error_msg = (
                                f"API错误: {event_data.get('message', '未知错误')}"
                            )
                            logger.error(error_msg)
                            if on_end:
                                on_end({"type": "text", "content": error_msg})
                            return {"type": "text", "content": error_msg}

                        elif event_type == "message_end":
                            conversation_id = event_data.get("conversation_id")
                            is_complete = True
                            break

                except json.JSONDecodeError:
                    logger.warning("解析流式响应失败: %s", data_line)
                    continue

        # 处理音频响应
        if audio_detected:
            try:
                # 从响应中提取音频URL
                url_match = re.search(r"\((https?://[^\)]+)\)", full_response)
                if url_match:
                    url = url_match.group(1).strip()
                    logger.info(f"检测到音频URL: {url}")

                    # 下载音频文件
                    audio_file_path = self._download_url_content(url)
                    if audio_file_path:
                        # 构建新的响应内容，包含文件路径标记
                        full_response = f"[AUDIO:{audio_file_path}]"
                    else:
                        logger.warning("音频文件下载失败")
                        full_response = "音频文件下载失败，请检查网络连接"
                else:
                    logger.warning("未找到有效的音频URL")
                    full_response = "未找到有效的音频下载链接"
            except Exception as e:
                logger.error(f"处理音频响应失败: {e}")
                full_response = f"处理音频响应时出错: {str(e)}"

        # 处理图片响应
        elif image_detected:
            try:
                # 从响应中提取图片URL
                url_match = re.search(r"\((https?://[^\)]+)\)", full_response)
                if url_match:
                    url = url_match.group(1).strip()
                    logger.info(f"检测到图片URL: {url}")

                    # 下载图片文件
                    image_file_path = self._download_image_content(url)
                    if image_file_path:
                        # 构建新的响应内容，包含文件路径标记
                        full_response = f"[IMAGE:{image_file_path}]"
                    else:
                        logger.warning("图片文件下载失败")
                        full_response = "图片文件下载失败，请检查网络连接"
                else:
                    logger.warning("未找到有效的图片URL")
                    full_response = "未找到有效的图片下载链接"
            except Exception as e:
                logger.error(f"处理图片响应失败: {e}")
                full_response = f"处理图片响应时出错: {str(e)}"

        # 更新会话ID
        if conversation_id:
            self.current_conversation_id = conversation_id

        # 构建最终响应
        final_response = {
            "conversation_id": conversation_id,
            "task_id": task_id,
            "audio_file_path": audio_file_path,
            "image_file_path": image_file_path,
            "content": full_response if not is_streaming else None,  # 流式响应时不返回完整内容
            "type": "text",
            "audio_detected": audio_detected,  # 添加音频检测标记
            "image_detected": image_detected,  # 添加图片检测标记
            "original_content": original_content  # 添加原始内容
        }

        # 通知UI响应结束
        if on_end and is_complete:
            on_end(final_response)

        return final_response

    def change_api_key(self, new_api_key):
           """修改 API 密钥"""
           self.api_key = new_api_key

    def _download_url_content(self, url):
        """下载URL内容到指定目录，强制使用.mp3格式"""
        print(f"[调试信息] 下载音频: {url}")

        try:
            # 确保下载目录存在
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir, exist_ok=True)

            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()

            # 计算文件总大小用于进度显示
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # 从响应头获取Content-Type和Content-Disposition
            content_type = response.headers.get("content-type", "")
            content_disposition = response.headers.get("content-disposition", "")

            # 尝试从Content-Disposition解析文件名
            filename = None
            if content_disposition:
                match = re.search(r'filename="(.*?)"', content_disposition)
                if match:
                    filename = match.group(1)
            # 如果没有从Content-Disposition获取到文件名，则使用时间戳生成文件名
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"audio_{timestamp}"
            # 强制使用.mp3扩展名
            filename = os.path.splitext(filename)[0] + ".mp3"
            # 保存文件到指定目录
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            logger.info(f"音频文件已下载到: {file_path}")
            print(f"[文件下载] 已下载音频到: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"下载音频文件失败: {e}")
            print(f"[错误] 音频下载失败: {str(e)}")
            return None

    def _download_image_content(self, url):
        """下载图片URL内容到与音频相同的目录，返回文件路径"""
        print(f"[调试信息] 下载图片: {url}")

        try:
            # 确保下载目录存在
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir, exist_ok=True)

            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # 从响应头获取Content-Disposition解析文件名
            content_disposition = response.headers.get("content-disposition", "")
            filename = None
            if content_disposition:
                match = re.search(r'filename="(.*?)"', content_disposition)
                if match:
                    filename = match.group(1)
            # 如果没有文件名，使用时间戳生成
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"image_{timestamp}"

            # 确定文件扩展名
            content_type = response.headers.get("content-type", "")
            if "image/jpeg" in content_type:
                ext = "jpg"
            elif "image/png" in content_type:
                ext = "png"
            elif "image/gif" in content_type:
                ext = "gif"
            else:
                ext = "jpg"  # 默认使用jpg

            filename = f"{os.path.splitext(filename)[0]}.{ext}"

            # 保存到下载目录
            file_path = os.path.join(self.download_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            logger.info(f"图片文件已下载到: {file_path}")
            print(f"[文件下载] 已下载图片到: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"下载图片文件失败: {e}")
            print(f"[错误] 图片下载失败: {str(e)}")
            return None

    def _open_image(self, file_path):
        """根据操作系统打开图片文件（仅在点击时调用）"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"图片文件不存在: {file_path}")
                return False

            # 根据不同操作系统使用相应的打开命令
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])

            logger.info(f"已打开图片: {file_path}")
            return True
        except Exception as e:
            logger.error(f"打开图片时出错: {e}")
            return False

    def _play_file(self, file_path, start_time=0):
        """播放音频文件，支持从指定时间开始播放"""
        if not os.path.exists(file_path):
            logger.warning(f"音频文件不存在，无法播放: {file_path}")
            return False

        try:
            # 如果已在播放同一文件，先暂停
            if file_path in self.playing_files:
                self._resume_file(file_path)
                return True

            # 加载音频文件
            pygame.mixer.music.load(file_path)

            # 从指定时间开始播放
            pygame.mixer.music.play(0, start_time)

            # 记录播放状态
            self.playing_files[file_path] = {
                "is_playing": True,
                "start_time": start_time,
                "paused": False
            }

            # 启动线程监控播放完成
            threading.Thread(target=self._monitor_playback, args=(file_path,), daemon=True).start()

            logger.info(f"已开始播放音频: {file_path}")
            return True

        except Exception as e:
            logger.error(f"播放音频文件时出错: {e}")
            return False

    def _monitor_playback(self, file_path):
        """监控音频播放状态，播放完成后设置事件"""
        while self.playing_files.get(file_path, {}).get("is_playing", False) and not self.playing_files[file_path].get("paused", True):
            time.sleep(0.5)

        # 播放完成或停止后设置事件
        self.audio_playback_completed.set()
        logger.info(f"音频播放完成: {file_path}")

    def _pause_file(self, file_path):
        """暂停音频播放"""
        if file_path not in self.playing_files:
            return False

        try:
            if not self.playing_files[file_path]["paused"]:
                pygame.mixer.music.pause()
                self.playing_files[file_path]["paused"] = True
                logger.info(f"已暂停播放音频: {file_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"暂停音频播放时出错: {e}")
            return False

    def _resume_file(self, file_path):
        """恢复音频播放"""
        if file_path not in self.playing_files:
            return False

        try:
            if self.playing_files[file_path]["paused"]:
                pygame.mixer.music.unpause()
                self.playing_files[file_path]["paused"] = False
                logger.info(f"已恢复播放音频: {file_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"恢复音频播放时出错: {e}")
            return False

    def _stop_file(self, file_path):
        """停止音频播放"""
        if file_path not in self.playing_files:
            return False

        try:
            pygame.mixer.music.stop()
            if file_path in self.playing_files:
                del self.playing_files[file_path]
            logger.info(f"已停止播放音频: {file_path}")

            # 重置播放完成事件
            self.audio_playback_completed.clear()
            return True

        except Exception as e:
            logger.error(f"停止音频播放时出错: {e}")
            return False

    def is_playing(self, file_path):
        """检查音频文件是否正在播放"""
        return file_path in self.playing_files and self.playing_files[file_path]["is_playing"] and not self.playing_files[file_path]["paused"]

    def get_playback_time(self, file_path):
        """获取当前播放时间（秒）"""
        if file_path in self.playing_files and not self.playing_files[file_path]["paused"]:
            return pygame.mixer.music.get_pos() / 1000  # 转换为秒
        return 0