"""
淘宝图片切分工具（带图形界面）
按照得力的图片风格，处理官网下载的xq.jpg以便上传到淘宝素材
"""

import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import threading
import time

from file.file_utils import read_chinese_path_image, cv2_imwrite_chinese,get_non_hidden_files_deli_xq


class ImageSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片切分工具")
        self.root.geometry("650x500")
        self.root.resizable(True, True)

        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TProgressbar", thickness=20)

        # 变量初始化
        self.target_directory = tk.StringVar()
        self.processed_count = 0
        self.total_files = 0
        self.is_processing = False

        self.create_widgets()

    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 目录选择区域
        dir_frame = ttk.LabelFrame(main_frame, text="图片目录", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)

        ttk.Label(dir_frame, text="目录路径:").pack(side=tk.LEFT, padx=5)

        dir_entry = ttk.Entry(dir_frame, textvariable=self.target_directory, width=45)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_btn = ttk.Button(dir_frame, text="浏览...", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # 操作按钮区域
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X, pady=5)

        self.process_btn = ttk.Button(btn_frame, text="开始处理", command=self.start_processing)
        self.process_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # 进度条区域
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.progress_label = ttk.Label(progress_frame, text="等待开始处理...")
        self.progress_label.pack(anchor=tk.W)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 日志文本框和滚动条
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, yscrollcommand=log_scroll.set, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        log_scroll.config(command=self.log_text.yview)

    def browse_directory(self):
        directory = filedialog.askdirectory(title="选择图片目录")
        if directory:
            self.target_directory.set(directory)

    def log(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 滚动到最后
        self.log_text.config(state=tk.DISABLED)

    def update_progress(self, value, message):
        """更新进度条和进度标签"""
        self.progress_var.set(value)
        self.progress_label.config(text=message)
        self.root.update_idletasks()

    def start_processing(self):
        """开始处理图片"""
        if self.is_processing:
            return

        directory = self.target_directory.get()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        self.is_processing = True
        self.process_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.processed_count = 0

        # 在新线程中处理，避免界面卡顿
        threading.Thread(target=self.process_images, args=(directory,), daemon=True).start()

    def cancel_processing(self):
        """取消处理"""
        self.is_processing = False
        self.process_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.log("已取消处理")

    def process_images(self, directory):
        """处理目录中的图片"""
        try:
            # 获取文件列表
            file_cache = get_non_hidden_files_deli_xq(directory)
            self.total_files = len(file_cache)

            if self.total_files == 0:
                self.log("未发现任何图片文件")
                self.finish_processing()
                return

            self.log(f"发现 {self.total_files} 个文件，开始处理...")
            self.update_progress(0, "准备处理...")

            for idx, file_path in enumerate(file_cache):
                if not self.is_processing:  # 检查是否取消
                    break

                try:
                    self.resize_image(file_path)
                    self.processed_count += 1
                    progress = (self.processed_count / self.total_files) * 100
                    self.update_progress(progress,
                                         f"已处理 {self.processed_count}/{self.total_files} "
                                         f"({progress:.1f}%) - {os.path.basename(file_path)}")
                    self.log(f"处理成功: {os.path.basename(file_path)}")
                except Exception as e:
                    self.log(f"处理失败 {os.path.basename(file_path)}: {str(e)}")

            if self.is_processing:
                self.log("所有文件处理完成")
            else:
                self.log(f"处理中断，已处理 {self.processed_count}/{self.total_files} 个文件")

        except Exception as e:
            self.log(f"处理过程出错: {str(e)}")
        finally:
            self.finish_processing()

    def finish_processing(self):
        """完成处理后的清理工作"""
        self.is_processing = False
        self.root.after(0, lambda: self.process_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.cancel_btn.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.update_progress(
            100 if self.processed_count == self.total_files else self.progress_var.get(),
            f"处理结束，共处理 {self.processed_count}/{self.total_files} 个文件"))

    def get_file_new_path(self, path):
        """获取新的文件路径"""
        file_directory = os.path.dirname(path)
        file_name = os.path.basename(path)
        file_name_without_ext, file_extension = os.path.splitext(file_name)

        new_path = os.path.join(file_directory,
                                file_name_without_ext.replace('扫描全能王 ', '') + '_800x800' + file_extension)

        return new_path

    def preprocess_image(self, img_cv):
        """图像预处理以提高二维码识别率"""
        # 转换为灰度图
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 高斯模糊去除噪声
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # 自适应阈值处理
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresh

    def blur_qrcode_opencv(self, img_cv):
        """使用OpenCV识别并模糊图片中的二维码"""
        # 创建原始图像的副本用于最终处理
        img_copy = img_cv.copy()

        # 对图像进行预处理以提高识别率
        processed = self.preprocess_image(img_cv)

        # 初始化QR码检测器
        qr_detector = cv2.QRCodeDetector()

        # 尝试多种方式检测二维码
        detection_methods = [
            (img_cv, "原始图像"),
            (processed, "预处理图像"),
            (cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY), "灰度图像")
        ]

        for img, method in detection_methods:
            retval, _, points, _ = qr_detector.detectAndDecodeMulti(img)

            if retval:
                self.log(f"使用{method}识别到二维码")
                # 转换为整数坐标
                points = np.int32(points)

                # 对每个检测到的二维码进行处理
                for qr_points in points:
                    # 计算二维码边界框
                    x_min, y_min = np.min(qr_points, axis=0)
                    x_max, y_max = np.max(qr_points, axis=0)

                    # 稍微扩大边界框，确保完全覆盖二维码
                    expand = 5
                    x_min = max(0, x_min - expand)
                    y_min = max(0, y_min - expand)
                    x_max = min(img_cv.shape[1] - 1, x_max + expand)
                    y_max = min(img_cv.shape[0] - 1, y_max + expand)

                    # 提取二维码区域并模糊
                    qr_roi = img_copy[y_min:y_max + 1, x_min:x_max + 1]
                    blurred_roi = cv2.GaussianBlur(qr_roi, (31, 31), 0)
                    img_copy[y_min:y_max + 1, x_min:x_max + 1] = blurred_roi

                return img_copy

        # 如果所有方法都无法识别，返回原图
        return img_copy

    def split_image_into_squares(self, img, output_dir, file_name):
        """将图片上下拆分为正方形片段"""
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        try:
            # 获取图片尺寸
            height, width = img.shape[:2]

            # 使用图片宽度作为每个正方形片段的高度
            segment_height = width

            # 计算可以分成多少段
            num_segments = (height + segment_height - 1) // segment_height

            # 拆分图片
            for i in range(num_segments):
                start_y = i * segment_height
                end_y = start_y + segment_height

                # 确保不超过图片高度
                if end_y > height:
                    end_y = height

                # 裁剪图片
                segment = img[start_y:end_y, :width]

                # 生成输出文件名
                output_path = os.path.join(output_dir, f"{file_name}_{i + 1:02d}.png")

                # 保存分段图片
                cv2_imwrite_chinese(output_path, segment)
                # cv2.imwrite(output_path, segment)

        except Exception as e:
            raise Exception(f"拆分图片时出错: {str(e)}")

    def resize_image(self, input_path):
        """处理单个图片：模糊二维码并拆分"""
        path = Path(input_path)
        if not path.exists() or path.is_dir():
            raise Exception("文件不存在或为目录")

        # 使用OpenCV读取图片
        img_cv = read_chinese_path_image(input_path)
        if img_cv is None:
            raise Exception("无法读取图片")

        # 识别并模糊原始图片中的二维码
        img_with_blur = self.blur_qrcode_opencv(img_cv)

        # 拆分图片
        output_dir = path.parent
        self.split_image_into_squares(img_with_blur, output_dir, path.stem)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSplitterApp(root)
    root.mainloop()
