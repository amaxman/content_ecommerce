import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import warnings

# 第三方库导入
from moviepy.video.io.VideoFileClip import VideoFileClip
import speech_recognition as sr
import whisper
import cv2
import easyocr
import time


class VideoToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频转文字工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 初始化变量
        self.model = None
        self.selected_file = None
        self.processing = False

        # 创建UI组件
        self._create_widgets()

        # 预加载whisper模型（后台线程）
        self._load_model_in_background()

    def _create_widgets(self):
        # 1. 顶部选择文件区域
        frame_select = ttk.LabelFrame(self.root, text="文件选择")
        frame_select.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frame_select, text="选择MP4视频文件:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(frame_select, textvariable=self.file_var)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(frame_select, text="浏览", command=self._browse_file).grid(row=0, column=2, padx=5, pady=5)

        # 2. 模型状态区域
        frame_model = ttk.LabelFrame(self.root, text="模型状态")
        frame_model.pack(fill=tk.X, padx=10, pady=5)

        self.model_status_var = tk.StringVar(value="模型加载中...")
        ttk.Label(frame_model, textvariable=self.model_status_var).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        # 3. 处理按钮区域
        frame_action = ttk.Frame(self.root)
        frame_action.pack(fill=tk.X, padx=10, pady=10)

        self.process_btn = ttk.Button(
            frame_action,
            text="开始转换",
            command=self._start_processing,
            state=tk.DISABLED
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(frame_action, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=5)

        # 4. 日志输出区域
        frame_log = ttk.LabelFrame(self.root, text="处理日志")
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 滚动条
        scrollbar = ttk.Scrollbar(frame_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 文本框
        self.log_text = tk.Text(frame_log, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.log_text.yview)

        # 布局权重设置
        frame_select.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

    def _browse_file(self):
        """浏览选择MP4文件"""
        file_path = filedialog.askopenfilename(
            title="选择MP4视频文件",
            filetypes=[("MP4文件", "*.mp4"), ("所有文件", "*.*")]
        )
        if file_path:
            self.selected_file = file_path
            self.file_var.set(file_path)
            if self.model and not self.processing:
                self.process_btn.config(state=tk.NORMAL)
            self._log(f"已选择文件: {file_path}")

    def _load_model_in_background(self):
        """后台加载whisper模型"""

        def load_model():
            try:
                self.model = self._load_whisper_with_mps("/Users/tyrtao/AI/文字识别/语音识别/whisper/medium.pt")
                self.model_status_var.set("模型加载完成（CPU模式）")
                self._log("Whisper模型加载完成")
                if self.selected_file:
                    self.process_btn.config(state=tk.NORMAL)
            except Exception as e:
                self.model_status_var.set("模型加载失败")
                self._log(f"模型加载出错: {str(e)}")
                messagebox.showerror("错误", f"模型加载失败: {str(e)}")

        # 启动后台线程加载模型
        threading.Thread(target=load_model, daemon=True).start()

    def _start_processing(self):
        """开始处理视频（后台线程）"""
        if not self.selected_file or self.processing:
            return

        self.processing = True
        self.process_btn.config(state=tk.DISABLED)
        self._log("开始处理视频，请稍候...")

        # 后台线程处理，避免界面卡死
        def process():
            try:
                # 1. 音频转文字
                self._log("提取音频并转换为文字...")
                audio_text = self._mp4_to_text(self.selected_file, self.model)
                self._log(f"音频识别结果: {audio_text[:50]}...")

                # 2. 视频画面文字识别
                self._log("识别视频画面中的文字...")
                video_texts = self._video_text_recognition(self.selected_file)
                self._log(f"画面识别到 {len(video_texts)} 条文字")

                # 3. 保存结果
                save_path = os.path.join(
                    Path(self.selected_file).parent,
                    Path(self.selected_file).stem + "_识别结果.txt"
                )
                self._save_text_to_file(save_path, audio_text + "\n\n=== 画面识别文字 ===\n" + "\n".join(video_texts))
                self._log(f"结果已保存至: {save_path}")
                self._log(f"处理完成！\n结果已保存至:\n{save_path}")

                # messagebox.showinfo("成功", f"处理完成！\n结果已保存至:\n{save_path}")
            except Exception as e:
                self._log(f"处理出错: {str(e)}")
                # messagebox.showerror("错误", f"处理失败: {str(e)}")
            finally:
                self.processing = False
                self.process_btn.config(state=tk.NORMAL)

        threading.Thread(target=process, daemon=True).start()

    def _log(self, msg):
        """日志输出"""
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self._log("日志已清空")

    # 核心功能函数（复用原有逻辑）
    def _load_whisper_with_mps(self, model_path_or_size="base"):
        """加载whisper模型（兼容CPU）"""

        # 过滤FP16警告
        def filter_fp16_warning(message, category, filename, lineno, file=None, line=None):
            if "FP16 is not supported on CPU; using FP32 instead" in str(message):
                return
            warnings.showwarning(message, category, filename, lineno, file, line)

        warnings.showwarning = filter_fp16_warning

        self._log("未检测到MPS支持，使用CPU运行")
        device = "cpu"
        model = whisper.load_model(model_path_or_size, device=device)
        return model

    def _mp4_to_text(self, mp4_path, model):
        """音频转文字"""
        if not os.path.exists(mp4_path) or not mp4_path.lower().endswith('.mp4'):
            raise ValueError("请提供有效的MP4文件路径")

        with VideoFileClip(mp4_path) as video:
            audio = video.audio
            temp_audio_path = os.path.join(Path(mp4_path).parent, Path(mp4_path).stem + ".wav")
            audio.write_audiofile(temp_audio_path, logger=None)

        result = model.transcribe(
            temp_audio_path,
            language="zh",
            fp16=False,
            initial_prompt="以下是简体中文的语音内容，识别结果请使用简体中文输出，避免使用繁体字。",
            verbose=False
        )
        text = result["text"]

        # 清理临时文件
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        return text

    def _video_text_recognition(self, video_path, lang=['ch_sim', 'en']):
        """视频画面文字识别"""
        results = []

        reader = easyocr.Reader(lang
                                , model_storage_directory='/Users/tyrtao/AI/文字识别/easyOCR'  # 你的模型存放目录
                                , download_enabled=False  # 禁用自动下载,
                                , gpu=False
                                )  # 若有GPU可设为True

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频：{video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        self._log(f"视频信息：时长{duration:.1f}秒，帧率{fps:.1f}")

        sample_interval = max(1, int(fps * 1.5))
        max_size = 640
        seen_texts = set()
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % sample_interval == 0:
                h, w = frame.shape[:2]
                if max(h, w) > max_size:
                    scale = max_size / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                try:
                    ocr_result = reader.readtext(frame_gray, detail=1)
                    for _, text, score in ocr_result:
                        if score > 0.6 and text.strip():
                            text_clean = text.strip().lower()
                            if text_clean not in seen_texts:
                                seen_texts.add(text_clean)
                                results.append(text.strip())
                                self._log(f"画面识别到：{text.strip()}")
                except Exception as e:
                    self._log(f"模型加载出错: {str(e)}")
            frame_count += 1

        cap.release()
        cv2.destroyAllWindows()
        return results

    def _save_text_to_file(self, file_path, text):
        """保存文字到文件"""
        if not text or len(text) <= 20:
            raise ValueError("识别结果为空或过短，无需保存")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToTextApp(root)
    root.mainloop()
