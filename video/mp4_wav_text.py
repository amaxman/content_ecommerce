import os
import threading
import time
import tkinter as tk
import warnings
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import whisper
# 第三方库导入
from moviepy.video.io.VideoFileClip import VideoFileClip


class VideoToTextApp2:
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
        """浏览选择目录"""
        dir_path = filedialog.askdirectory(title="选择存放MP4视频的文件夹")
        if dir_path:
            self.selected_file = dir_path
            self.file_var.set(dir_path)
            if self.model and not self.processing:
                self.process_btn.config(state=tk.NORMAL)
            self._log(f"已选择处理目录: {dir_path}")

    def _load_model_in_background(self):
        """后台加载whisper模型"""

        def load_model():
            try:
                self.model, run_model = self._load_whisper_with_mps(
                    "/Users/tyrtao/AI/文字识别/语音识别/whisper/small.pt")
                self.model_status_var.set("模型加载完成（" + run_model + "模式）")
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
        """批量处理目录下所有MP4，后台线程执行"""
        if not self.selected_file or self.processing:
            return
        # 判断选中的是目录还是文件
        target_dir = Path(self.selected_file)
        if not target_dir.is_dir():
            self._log("当前选择不是目录，请重新选择文件夹！")
            return

        self.processing = True
        self.process_btn.config(state=tk.DISABLED)
        self._log(f"开始批量处理目录：{target_dir}")

        # 后台线程处理
        def process():
            try:
                # 遍历目录下所有mp4
                mp4_list = list(target_dir.glob("*.MP4"))
                if not mp4_list:
                    self._log("目录内未找到任何MP4文件")
                    return
                self._log(f"共找到 {len(mp4_list)} 个MP4文件")
                for idx, mp4_path in enumerate(mp4_list, 1):
                    self._log(f"\n===== 正在处理({idx}/{len(mp4_list)})：{mp4_path.name} =====")
                    # 音频转文字
                    audio_text = self._mp4_to_text(str(mp4_path), self.model)
                    self._log(f"音频识别结果预览：{audio_text[:80]}...")
                    # 保存语音文本
                    save_path = os.path.join(mp4_path.parent, mp4_path.stem + "_语音识别.txt")
                    self._save_text_to_file(save_path, audio_text)
                    self._log(f"结果保存至：{save_path}")
                self._log("\n===== 全部文件处理完成 =====")
            except Exception as e:
                self._log(f"批量处理出错: {str(e)}")
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

    # 核心功能函数（ # 核心功能函数（复用原有逻辑）
    def _load_whisper_with_mps_init(self, model_path_or_size="base"):
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

    def _load_whisper_with_mps(self, model_path_or_size="base"):
        import torch
        # 过滤FP16无关警告
        def filter_fp16_warning(message, category, filename, lineno, file=None, line=None):
            if "FP16 is not supported on CPU; using FP32 instead" in str(message):
                return

        warnings.showwarning = filter_fp16_warning

        self._log("第一步：CPU加载模型，规避MPS稀疏张量报错")
        # 1 强制先在CPU加载（唯一能处理稀疏权重的设备）
        model = whisper.load_model(model_path_or_size, device="cpu")

        # 2 遍历所有权重、缓冲，稀疏张量全部转密集张量（关键修复）
        for _, module in model.named_modules():
            # 转换稀疏weight
            if hasattr(module, "weight") and isinstance(module.weight, torch.Tensor):
                if module.weight.is_sparse:
                    module.weight = torch.nn.Parameter(module.weight.to_dense())
            # 转换所有稀疏buffer
            for buf_name, buf in module.named_buffers():
                if isinstance(buf, torch.Tensor) and buf.is_sparse:
                    dense_buf = buf.to_dense()
                    setattr(module, buf_name, dense_buf)

        run_model = ''
        # 3 检测MPS并迁移模型到GPU
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            self._log("✅ MPS GPU可用，模型迁移至Metal加速")
            model = model.to("mps")
            run_model = 'mps'
        else:
            self._log("❌ 当前设备不支持MPS，继续使用CPU")
            run_model = 'cpu'

        return model, run_model

    def _mp4_to_text(self, mp4_path, model):
        """音频转文字"""
        if not os.path.exists(mp4_path) or not mp4_path.lower().endswith('.mp4'):
            raise ValueError("请提供有效的MP4文件路径")
        with VideoFileClip(mp4_path) as video:
            audio = video.audio
            temp_audio_path = os.path.join(Path(mp4_path).parent, Path(mp4_path).stem + ".wav")
            # audio.write_audiofile(temp_audio_path, logger=None)
            audio.write_audiofile(
                temp_audio_path,
                logger=None,
                codec="pcm_s16le",
                fps=16000,  # whisper仅需16k采样率，不用原视频高采样
                bitrate="128k"
            )
        # result = model.transcribe(
        #     temp_audio_path,
        #     language="zh",
        #     fp16=False,
        #     initial_prompt="以下是简体中文的语音内容，识别结果请使用简体中文输出，避免使用繁体字。",
        #     verbose=False
        # )

        result = model.transcribe(
            temp_audio_path,
            language="zh",
            fp16=False,
            initial_prompt="以下是简体中文",
            verbose=False,
            # 新增提速参数
            word_timestamps=False,  # 不生成字时间戳，节省计算
            condition_on_previous_text=False,  # 关闭上下文依赖，减少推理
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6
        )
        text = result["text"]
        # 清理临时文件
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        return text

    def _save_text_to_file(self, file_path, text):
        """保存文字到文件"""
        if not text or len(text) <= 20:
            raise ValueError("识别结果为空或过短，无需保存")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToTextApp2(root)
    root.mainloop()
