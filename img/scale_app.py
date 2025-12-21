import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from config import img_width, img_height  # 假设仍使用原配置
from file.file_utils import get_non_hidden_files_pathlib, read_chinese_path_image, cv2_imwrite_chinese


class ImageScaleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片缩放工具")
        self.root.geometry("600x400")

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):

        # 选择目录框架
        dir_frame = ttk.Frame(self.root, padding="10")
        dir_frame.pack(fill=tk.X)

        ttk.Label(dir_frame, text="目标目录:").pack(side=tk.LEFT, padx=5)

        current_dir = os.path.dirname(os.path.abspath(__file__))

        self.dir_var = tk.StringVar(value=current_dir)
        self.dir_entry = ttk.Entry(
            dir_frame,
            textvariable=self.dir_var,
            width=45)
        self.dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        browse_btn = tk.Button(
            dir_frame,
            text="浏览",
            command=self.browse_directory,
            fg="black",  # 明确设置文字颜色
            bg="SystemButtonFace",  # 使用系统按钮背景色
            width=6
        )
        browse_btn.pack(side=tk.LEFT, padx=5)

        # 处理按钮
        process_btn = ttk.Button(self.root, text="开始处理图片", command=self.start_processing)
        process_btn.pack(pady=10)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)

        # 日志区域
        log_frame = ttk.Frame(self.root, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="处理日志:").pack(anchor=tk.W)

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 禁用文本框编辑
        self.log_text.config(state=tk.DISABLED)

    def browse_directory(self):
        selected_dir = filedialog.askdirectory()
        # 确保用户选择了文件夹（未取消）
        if selected_dir:
            # 验证路径有效性（针对图片处理场景的额外检查）
            if os.path.isdir(selected_dir):
                self.dir_var.set(selected_dir)  # 设置变量值，输入框会自动更新
                print(f"已选择目录: {selected_dir}")
            else:
                tk.messagebox.showerror("错误", "所选路径不是有效的文件夹")

    def log(self, message):
        """向日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 滚动到最后
        self.log_text.config(state=tk.DISABLED)

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
                self.log(f"使用{method}成功识别到二维码")
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

                    # 提取二维码区域
                    qr_roi = img_copy[y_min:y_max + 1, x_min:x_max + 1]

                    # 应用更强的高斯模糊
                    blurred_roi = cv2.GaussianBlur(qr_roi, (31, 31), 0)

                    # 将模糊后的区域放回原图
                    img_copy[y_min:y_max + 1, x_min:x_max + 1] = blurred_roi

                return img_copy

        # 如果所有方法都无法识别，返回原图并提示
        self.log("未检测到二维码")
        return img_copy

    def resize_image(self, input_path, output_path):
        """先处理二维码，再根据长宽比旋转，最后调整图片大小"""
        try:
            # 使用OpenCV读取图片
            img_cv = read_chinese_path_image(input_path)
            if img_cv is None:
                self.log(f"无法读取图片: {input_path}")
                return False

            # 先识别并模糊原始图片中的二维码
            img_with_blur = self.blur_qrcode_opencv(img_cv)

            # 获取处理后的图片的宽和高
            height, width = img_with_blur.shape[:2]

            # 如果高度小于宽度，则旋转90度
            rotated = False
            if height < width:
                self.log(f"图片高度({height})小于宽度({width})，旋转90度")
                # 旋转90度（顺时针）
                img_with_blur = cv2.rotate(img_with_blur, cv2.ROTATE_90_CLOCKWISE)
                # 更新旋转后的尺寸
                height, width = img_with_blur.shape[:2]
                rotated = True

            # 检查是否已经是目标尺寸
            if width == img_width and height == img_height:
                cv2.imwrite(output_path, img_with_blur)
                return True

            # 计算缩放系数
            scale = min(img_width / width, img_height / height)

            # 计算缩放后的尺寸
            new_width = int(width * scale)
            new_height = int(height * scale)

            # 缩放图片
            resized_img = cv2.resize(img_with_blur, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

            # 创建指定尺寸的白色背景图片
            new_img = np.ones((img_height, img_width, 3), dtype=np.uint8) * 255

            # 计算粘贴位置（居中放置）
            paste_x = (img_width - new_width) // 2
            paste_y = (img_height - new_height) // 2

            # 将缩放后的图片粘贴到白色背景上
            new_img[paste_y:paste_y + new_height, paste_x:paste_x + new_width] = resized_img

            # 保存结果图片
            cv2_imwrite_chinese(output_path, new_img)
            # cv2.imwrite(output_path, new_img)

            return True

        except Exception as e:
            self.log(f"处理图片时出错: {str(e)}")
            return False

    def get_file_new_path(self,path):
        # 提取文件所在的目录路径
        file_directory = os.path.dirname(path)

        # 提取文件名（包含扩展名）
        file_name = os.path.basename(path)

        # 提取文件名（不包含扩展名）和扩展名
        file_name_without_ext, file_extension = os.path.splitext(file_name)

        # 将整数转换为字符串后拼接（使用f-string自动转换）
        new_path = os.path.join(
            file_directory,
            f"{file_name_without_ext.replace('扫描全能王 ', '')}_{img_width}x{img_height}{file_extension}"
        )

        return new_path

    def process_files(self):
        """处理文件的线程函数"""
        target_directory = self.dir_var.get()
        if not target_directory:
            self.log("请先选择目标目录")
            return

        try:
            # 获取文件列表
            file_cache = get_non_hidden_files_pathlib(target_directory)
            total_files = len(file_cache)
            self.log(f"发现 {total_files} 个文件路径")

            if total_files == 0:
                messagebox.showinfo("提示", "目录中没有找到文件")
                return

            # 处理每个文件
            for i, file_path in enumerate(file_cache):
                try:
                    self.log(f'=======开始处理: {file_path}=======')
                    if f'_{img_width}x{img_height}' in file_path:
                        self.log(f'文件名包含_{img_width}x{img_height}，已忽略')
                        continue

                    new_path = self.get_file_new_path(file_path)
                    result = self.resize_image(file_path, new_path)
                    if result:
                        os.remove(file_path)
                        self.log(f'已删除原文件: {file_path}')
                except Exception as e:
                    self.log(f"处理图片时出错: {str(e)}")
                finally:
                    self.log('=======处理结束=======')
                    # 更新进度条
                    progress = (i + 1) / total_files * 100
                    self.progress_var.set(progress)

            self.log("所有文件处理完成")
            messagebox.showinfo("完成", "所有文件处理完成")

        except ValueError as e:
            self.log(str(e))
        finally:
            # 重置进度条
            self.progress_var.set(0)

    def start_processing(self):
        """开始处理文件（在新线程中运行以避免界面冻结）"""
        # 检查目录是否存在
        target_directory = self.dir_var.get()
        if not target_directory or not os.path.exists(target_directory):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        # 在新线程中处理文件
        threading.Thread(target=self.process_files, daemon=True).start()

    def image_scale(self):
        """显示窗体的方法"""
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageScaleApp(root)
    app.image_scale()
