import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path
import easyocr
import cv2
import time
import numpy as np


# 初始化 EasyOCR 阅读器（提前加载，避免重复初始化）
def init_easyocr_reader():
    """初始化 EasyOCR 阅读器，复用你提供的配置"""
    try:
        reader = easyocr.Reader(
            ['ch_sim', 'en'],  # 中文简体 + 英文
            model_storage_directory='/Users/tyrtao/AI/文字识别/easyOCR',
            download_enabled=False,
            gpu=False
        )
        return reader
    except Exception as e:
        messagebox.showerror("初始化失败", f"EasyOCR 模型加载出错：{str(e)}")
        return None


# 核心识别函数（复用你的优化逻辑）
def recognize_image_text(image_path, reader, status_label):
    """识别单张图片文字，返回结果列表"""
    if not os.path.exists(image_path):
        status_label.config(text="错误：文件不存在")
        return []

    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
    if not image_path.lower().endswith(supported_formats):
        status_label.config(text="错误：仅支持图片格式（jpg/png/bmp等）")
        return []

    try:
        status_label.config(text="正在读取图片...")
        # 读取图片（兼容中文路径）
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            status_label.config(text="错误：图片读取失败")
            return []

        # # 优化：压缩图片
        # max_size = 640
        # h, w = img.shape[:2]
        # if max(h, w) > max_size:
        #     scale = max_size / max(h, w)
        #     img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # 转为灰度图
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        status_label.config(text="正在识别文字...")
        start_time = time.time()

        # 执行识别
        ocr_result = reader.readtext(
            img_gray,
            detail=1,  # 保留置信度等细节（必须）
            paragraph=False,  # 不合并为段落，保留单字/短句（避免漏检）
            min_size=5,  # 最小检测文字尺寸（默认20，降低后识别更小文字）
            contrast_ths=0.1,  # 对比度阈值（默认0.1，更低值适配低对比度文字）
            adjust_contrast=0.5,  # 自动增强对比度（0-1，提升模糊/淡色文字辨识度）
            text_threshold=0.4,  # 文字区域判定阈值（默认0.7，降低后检测更多候选区域）
            low_text=0.2,  # 低置信度文字阈值（默认0.4，更低值保留更多候选）
            link_threshold=0.4,  # 文字行连接阈值（默认0.4，微调适配断行文字）
            canvas_size=1280,  # 图像预处理画布尺寸（更大尺寸保留更多细节）
            mag_ratio=1.5,  # 放大比例（1.0-2.0，放大小文字）
            slope_ths=0.2,  # 文字行倾斜阈值（适配倾斜文字）
            ycenter_ths=0.5,  # 行内文字垂直对齐阈值（适配不规则排版）
            height_ths=0.5,  # 行高差异阈值（适配不同字号混排）
            width_ths=0.5,  # 字间距阈值（适配稀疏文字）
            add_margin=0.1,  # 文字区域边缘扩展（避免截断文字）
            threshold=0.3,  # 二值化阈值（更低值保留更多灰度细节）
            bbox_min_score=0.2,  # 检测框最小置信度（保留更多候选框）
            bbox_min_size=10,  # 检测框最小尺寸（识别更小文字）
        )

        return ocr_result
    except Exception as e:
        status_label.config(text=f"识别出错：{str(e)}")
        return None


def group_ocr_by_lines(ocr_result, line_threshold=10):
    """
    将OCR识别结果按行位置相近性分组

    Args:
        ocr_result (list): OCR识别结果列表，每个元素为 (bbox, text, confidence)
        line_threshold (int): 行间距阈值（像素），小于该值的文字块视为同一行

    Returns:
        list: 按行分组后的文本列表，每个元素为一行的完整文本
    """
    # 空值处理
    if not ocr_result:
        return []

    # 1. 按顶部纵坐标（bbox的第一个点的y值）排序，确保从上到下处理
    # 修复：从bbox中提取top坐标（y1），而非字典key
    sorted_blocks = sorted(ocr_result, key=lambda x: x[0][0][1])

    # 2. 按行分组
    lines = []
    current_line = [sorted_blocks[0]]  # 初始化第一行

    for block in sorted_blocks[1:]:
        # 计算当前块与当前行第一个块的top差值（y1）
        current_top = current_line[0][0][0][1]
        block_top = block[0][0][1]
        top_diff = abs(block_top - current_top)
        if top_diff <= line_threshold:
            # 位置相近，加入当前行
            current_line.append(block)
        else:
            # 位置较远，当前行结束，新建一行
            lines.append(current_line)
            current_line = [block]
    # 把最后一行加入结果
    lines.append(current_line)

    # 3. 每行内按left坐标（x1）排序，拼接文本
    final_lines = []
    for line in lines:
        # 按左侧横坐标（bbox第一个点的x值）排序，保证文字顺序正确
        sorted_line = sorted(line, key=lambda x: x[0][0][0])
        # 拼接该行的所有文本
        line_text = '   '.join([block[1] for block in sorted_line])
        final_lines.append(line_text)

    return final_lines


# TK 主界面类
class EasyOCRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyOCR 图片文字识别工具")
        self.root.geometry("800x600")  # 初始窗口大小
        self.root.resizable(True, True)

        # 初始化 EasyOCR 阅读器
        self.reader = init_easyocr_reader()
        if self.reader is None:
            root.quit()
            return

        # 选中的文件路径
        self.selected_file = tk.StringVar()

        # 构建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件，确保“开始识别”按钮可见"""
        # 1. 顶部文件选择区域
        frame_file = ttk.Frame(self.root, padding="10")
        frame_file.pack(fill=tk.X, anchor=tk.N, expand=False)  # 确保框架不挤压按钮

        ttk.Label(frame_file, text="选择图片：").pack(side=tk.LEFT, padx=5)
        # 调整输入框宽度，避免挤压按钮
        entry = ttk.Entry(frame_file, textvariable=self.selected_file, width=40)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 浏览按钮
        ttk.Button(frame_file, text="浏览", command=self._browse_file).pack(side=tk.LEFT, padx=5)
        # 开始识别按钮：显式设置宽度+确保pack顺序，保证可见
        self.recognize_btn = ttk.Button(
            frame_file,
            text="开始识别",
            command=self._start_recognize,
            width=10  # 固定宽度，避免被挤压
        )
        self.recognize_btn.pack(side=tk.LEFT, padx=5)
        self.recognize_btn.config(state=tk.NORMAL)  # 确保按钮可用且可见

        # 2. 状态提示标签
        self.status_label = ttk.Label(self.root, text="就绪 - 请选择图片并点击识别", foreground="blue")
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # 3. 结果显示区域
        frame_result = ttk.Frame(self.root, padding="10")
        frame_result.pack(fill=tk.BOTH, expand=True, anchor=tk.N)

        ttk.Label(frame_result, text="识别结果：").pack(anchor=tk.W)
        self.result_text = scrolledtext.ScrolledText(frame_result, wrap=tk.WORD, width=90, height=25)
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 4. 底部操作按钮
        frame_oper = ttk.Frame(self.root, padding="10")
        frame_oper.pack(fill=tk.X, anchor=tk.S)

        ttk.Button(frame_oper, text="清空结果", command=self._clear_result).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_oper, text="保存结果", command=self._save_result).pack(side=tk.LEFT, padx=5)

    def _browse_file(self):
        """打开文件选择对话框"""
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.selected_file.set(file_path)
            self.status_label.config(text="已选择文件：" + os.path.basename(file_path))

    def _start_recognize(self):
        """开始识别图片文字（修复结果处理逻辑+确保按钮交互正常）"""
        file_path = self.selected_file.get().strip()
        if not file_path:
            messagebox.showwarning("提示", "请先选择要识别的图片文件！")
            return

        # 清空原有结果
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="正在识别，请稍候...")
        self.root.update()  # 立即更新UI，避免卡顿

        # 执行识别
        results = recognize_image_text(file_path, self.reader, self.status_label)

        # 显示结果（修复：调用分组函数并输出结果）
        if results and len(results) > 0:
            # 按行分组
            line_texts = group_ocr_by_lines(results, line_threshold=10)
            # 将分行结果插入文本框
            for line in line_texts:
                self.result_text.insert(tk.END, line + "\n")
            self.status_label.config(text=f"识别完成！共识别 {len(line_texts)} 行文字")
        else:
            self.result_text.insert(tk.END, "未识别到有效文字")
            self.status_label.config(text="识别完成 - 未识别到有效文字")

    def _clear_result(self):
        """清空结果框"""
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="结果已清空")

    def _save_result(self):
        """保存识别结果到文件"""
        result_content = self.result_text.get(1.0, tk.END).strip()
        if not result_content:
            messagebox.showwarning("提示", "无识别结果可保存！")
            return

        # 选择保存路径
        save_path = filedialog.asksaveasfilename(
            title="保存识别结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(result_content)
                messagebox.showinfo("成功", f"结果已保存至：{save_path}")
                self.status_label.config(text="结果保存成功")
            except Exception as e:
                messagebox.showerror("保存失败", f"文件保存出错：{str(e)}")


# 程序入口
if __name__ == "__main__":
    root = tk.Tk()
    app = EasyOCRGUI(root)
    root.mainloop()