import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import ffmpeg


class AudioConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("音频格式转换器 (FLAC/OGG → MP3)")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        # 初始化变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.bitrate = tk.StringVar(value="320k")  # 默认高质量
        self.is_converting = False

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):
        # ========== 输入选择区域 ==========
        frame_input = ttk.LabelFrame(self.root, text="输入选择", padding=(10, 5))
        frame_input.pack(fill="x", padx=20, pady=10)

        ttk.Label(frame_input, text="输入路径:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame_input, textvariable=self.input_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="选择文件", command=self.select_input_file).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(frame_input, text="选择目录", command=self.select_input_dir).grid(row=0, column=3, padx=5, pady=5)

        # ========== 输出选择区域 ==========
        frame_output = ttk.LabelFrame(self.root, text="输出设置", padding=(10, 5))
        frame_output.pack(fill="x", padx=20, pady=10)

        ttk.Label(frame_output, text="输出目录:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame_output, textvariable=self.output_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_output, text="选择目录", command=self.select_output_dir).grid(row=0, column=2, padx=5, pady=5)

        # 比特率选择
        ttk.Label(frame_output, text="MP3 比特率:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        bitrate_options = ["128k", "192k", "256k", "320k"]
        ttk.Combobox(frame_output, textvariable=self.bitrate, values=bitrate_options, width=10).grid(row=1, column=1,
                                                                                                     sticky="w", padx=5,
                                                                                                     pady=5)

        # ========== 转换控制区域 ==========
        frame_control = ttk.Frame(self.root, padding=(10, 5))
        frame_control.pack(fill="x", padx=20, pady=10)

        self.convert_btn = ttk.Button(frame_control, text="开始转换", command=self.start_conversion)
        self.convert_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(frame_control, text="停止转换", command=self.stop_conversion, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # ========== 日志显示区域 ==========
        frame_log = ttk.LabelFrame(self.root, text="转换日志", padding=(10, 5))
        frame_log.pack(fill="both", expand=True, padx=20, pady=10)

        # 滚动条
        scrollbar = ttk.Scrollbar(frame_log)
        scrollbar.pack(side="right", fill="y")

        # 日志文本框
        self.log_text = tk.Text(frame_log, wrap="word", yscrollcommand=scrollbar.set, height=15)
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # 清空日志按钮
        ttk.Button(frame_log, text="清空日志", command=self.clear_log).pack(side="bottom", pady=5)

    def select_input_file(self):
        """选择单个输入文件"""
        file_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[("音频文件", "*.flac *.ogg"), ("FLAC 文件", "*.flac"), ("OGG 文件", "*.ogg"),
                       ("所有文件", "*.*")]
        )
        if file_path:
            self.input_path.set(file_path)

    def select_input_dir(self):
        """选择输入目录"""
        dir_path = filedialog.askdirectory(title="选择输入目录")
        if dir_path:
            self.input_path.set(dir_path)

    def select_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_path.set(dir_path)

    def log(self, message):
        """添加日志信息"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")  # 自动滚动到最后
        self.root.update_idletasks()  # 刷新界面

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, "end")

    def start_conversion(self):
        """开始转换（放到子线程执行，避免界面卡死）"""
        # 验证输入输出路径
        input_target = self.input_path.get().strip()
        output_folder = self.output_path.get().strip()

        if not input_target:
            messagebox.showerror("错误", "请选择输入文件或目录！")
            return
        if not output_folder:
            messagebox.showerror("错误", "请选择输出目录！")
            return
        if not os.path.exists(input_target):
            messagebox.showerror("错误", f"输入路径不存在：{input_target}")
            return

        # 禁用按钮，防止重复点击
        self.is_converting = True
        self.convert_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        # 清空日志
        self.clear_log()
        self.log("===== 开始转换 =====")
        self.log(f"输入路径: {input_target}")
        self.log(f"输出目录: {output_folder}")
        self.log(f"比特率: {self.bitrate.get()}")
        self.log("-" * 50)

        # 子线程执行转换
        conversion_thread = threading.Thread(
            target=self.run_conversion,
            args=(input_target, output_folder, self.bitrate.get()),
            daemon=True
        )
        conversion_thread.start()

    def stop_conversion(self):
        """停止转换"""
        self.is_converting = False
        self.stop_btn.config(state="disabled")
        self.log("===== 用户终止转换 =====")

    def run_conversion(self, input_target, output_folder, bitrate):
        """实际执行转换逻辑"""
        try:
            if os.path.isfile(input_target):
                # 转换单个文件
                self.convert_single_file(input_target, output_folder, bitrate)
            elif os.path.isdir(input_target):
                # 批量转换目录
                self.batch_convert_folder(input_target, output_folder, bitrate)

            if self.is_converting:  # 如果不是用户终止
                self.log("-" * 50)
                self.log("===== 转换完成 =====")
        except Exception as e:
            self.log(f"转换出错：{str(e)}")
        finally:
            # 恢复按钮状态
            self.is_converting = False
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled"))

    def convert_single_file(self, input_path, output_folder, bitrate):
        """转换单个文件"""
        try:
            # 检查文件格式
            if not input_path.lower().endswith((".flac", ".ogg")):
                self.log(f"❌ 不支持的格式：{input_path}")
                return

            # 构建输出路径
            file_name = os.path.basename(input_path)
            output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + ".mp3")

            # 执行转换
            (
                ffmpeg
                .input(input_path)
                .output(output_path, audio_bitrate=bitrate)
                .overwrite_output()
                .run(quiet=True)
            )
            self.log(f"✅ 转换成功：{file_name}")
        except Exception as e:
            self.log(f"❌ 转换失败：{os.path.basename(input_path)} - {str(e)}")

    def batch_convert_folder(self, input_folder, output_folder, bitrate):
        """批量转换目录"""
        supported_formats = (".flac", ".ogg")
        file_count = 0
        success_count = 0

        # 遍历目录
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                # 检查是否需要停止
                if not self.is_converting:
                    return

                if file.lower().endswith(supported_formats):
                    file_count += 1
                    input_path = os.path.join(root, file)

                    # 构建输出路径（保持目录结构）
                    relative_path = os.path.relpath(input_path, input_folder)
                    output_path = os.path.join(output_folder, relative_path)
                    output_path = os.path.splitext(output_path)[0] + ".mp3"

                    # 确保输出目录存在
                    output_dir = os.path.dirname(output_path)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    # 转换文件
                    try:
                        (
                            ffmpeg
                            .input(input_path)
                            .output(output_path, audio_bitrate=bitrate)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                        self.log(f"✅ [{file_count}] {file}")
                        success_count += 1
                    except Exception as e:
                        self.log(f"❌ [{file_count}] {file} - {str(e)}")

        # 输出统计信息
        self.log("-" * 50)
        self.log(f"📊 总计：找到 {file_count} 个音频文件，成功转换 {success_count} 个")


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioConverterGUI(root)
    root.mainloop()
