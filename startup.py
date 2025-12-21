import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from img.scale_app import ImageScaleApp
from img.splitter_app import ImageSplitterApp


class NormalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("庆辰AI")
        self.root.geometry("400x400")
        # 允许窗体缩放（自适应的前提）
        self.root.resizable(True, True)

        # ========== 主容器 ==========
        self.main_container = ttk.Frame(root)
        # 移除额外边距，让主容器铺满窗体（仅保留2px边距做边界）
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        # 配置主容器的grid权重：第1行（九宫格）占满剩余空间，3列平均分配
        self.main_container.grid_rowconfigure(0, weight=0)
        for col in range(3):
            self.main_container.grid_columnconfigure(col, weight=1)

        # ========== 窗体标题 ==========
        self.title_label = ttk.Label(
            self.main_container,
            text="功能操作面板",
            font=("微软雅黑", 16, "bold")
        )
        # 减小标题边距，避免过多空白
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(5, 10))

        # ========== 加载图片（本地图片/默认占位图，存储原始图片用于自适应） ==========
        img_path = "resources/images/resize.png"
        self.img_config = {
            "new": {"path": img_path, "color": (200, 200, 200)},
            "exit": {"path": img_path, "color": (255, 100, 100)},
            "scale": {"path": img_path, "color": (100, 200, 100)},
            "split": {"path": img_path, "color": (100, 100, 200)},
            "qrcode": {"path": img_path, "color": (200, 200, 100)},
            "watermark": {"path": img_path, "color": (200, 100, 200)},
            "text": {"path": img_path, "color": (100, 200, 200)},
        }
        self.original_imgs = {}  # 存储原始PIL图片
        self.tk_imgs = {}  # 存储tkinter可用的图片对象
        # 初始化加载原始图片
        for name, config in self.img_config.items():
            try:
                self.original_imgs[name] = Image.open(config["path"])
            except FileNotFoundError:
                # 创建默认纯色图
                self.original_imgs[name] = Image.new("RGB", (32, 32), config["color"])
        # 初始化图片尺寸（默认32x32）
        self.update_image_size(32, 32, True)

        # ========== 九宫格功能面板 ==========
        self.grid_panel = ttk.Frame(self.main_container)
        # 让九宫格面板铺满主容器的第1行，3列
        self.grid_panel.grid(row=1, column=0, columnspan=3, sticky="nsew")
        # 配置九宫格面板的3行3列，每一行每一列都平均分配空间（权重为1）
        for row in range(3):
            self.grid_panel.grid_rowconfigure(row, weight=1)
        for col in range(3):
            self.grid_panel.grid_columnconfigure(col, weight=1)

        # ========== 按钮样式（移除内边距，让按钮内容贴合单元格） ==========
        self.style = ttk.Style()
        self.style.configure(
            "Func.TButton",
            font=("微软雅黑", 10),
            padding=2  # 仅保留2px内边距，避免文字/图片贴边
        )

        # 空单元格用Frame填充，同样铺满单元格
        self.empty1 = ttk.Frame(self.grid_panel)
        self.empty1.grid(row=0, column=2, sticky="nsew")

        # ---------------- 第二组：图片处理（九宫格第二行） ----------------
        self.btn_img_scale = ttk.Button(
            self.grid_panel,
            text="图片缩放",
            image=self.tk_imgs["scale"],
            compound=tk.LEFT,
            command=self.image_scale,
            style="Func.TButton"
        )
        self.btn_img_scale.grid(row=0, column=0, sticky="nsew")

        self.btn_img_split = ttk.Button(
            self.grid_panel,
            text="图片拆分",
            image=self.tk_imgs["split"],
            compound=tk.LEFT,
            command=self.image_split,
            style="Func.TButton"
        )
        self.btn_img_split.grid(row=0, column=1, sticky="nsew")

        self.btn_img_qrcode = ttk.Button(
            self.grid_panel,
            text="检测二维码",
            image=self.tk_imgs["qrcode"],
            compound=tk.LEFT,
            command=self.image_qrcode_detect,
            style="Func.TButton"
        )
        self.btn_img_qrcode.grid(row=0, column=2, sticky="nsew")

        # ---------------- 第三组：视频处理（九宫格第三行） ----------------
        self.btn_video_watermark = ttk.Button(
            self.grid_panel,
            text="移除水印",
            image=self.tk_imgs["watermark"],
            compound=tk.LEFT,
            command=self.video_remove_watermark,
            style="Func.TButton"
        )
        self.btn_video_watermark.grid(row=1, column=0, sticky="nsew")

        self.btn_video_text = ttk.Button(
            self.grid_panel,
            text="提取文字",
            image=self.tk_imgs["text"],
            compound=tk.LEFT,
            command=self.video_extract_text,
            style="Func.TButton"
        )
        self.btn_video_text.grid(row=1, column=1, sticky="nsew")

        # 空单元格用Frame填充
        self.empty2 = ttk.Frame(self.grid_panel)
        self.empty2.grid(row=1, column=2, sticky="nsew")

        # ========== 绑定窗体大小变化事件，动态调整图片大小+确保按钮铺满单元格 ==========
        self.root.bind("<Configure>", self.on_window_resize)

    def update_image_size(self, width, height, init=False):
        """更新图片尺寸并转换为tkinter可用格式"""
        for name, img in self.original_imgs.items():
            # 调整图片大小，保持比例
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            self.tk_imgs[name] = ImageTk.PhotoImage(img_resized)
        # 初始化时不更新按钮（按钮还未创建），非初始化时更新
        if not init:
            self.btn_img_scale.config(image=self.tk_imgs["scale"])
            self.btn_img_split.config(image=self.tk_imgs["split"])
            self.btn_img_qrcode.config(image=self.tk_imgs["qrcode"])
            self.btn_video_watermark.config(image=self.tk_imgs["watermark"])
            self.btn_video_text.config(image=self.tk_imgs["text"])

    def on_window_resize(self, event):
        """窗体大小变化时，动态调整图片大小+确保按钮铺满单元格"""
        # 过滤无效的resize事件（窗体尺寸过小时）
        if event.width < 200 or event.height < 200:
            return
        # 计算图片新尺寸（按九宫格单元格大小的1/5缩放，保持比例）
        cell_width = (event.width - 4) // 3  # 减去主容器的2px边距*2
        cell_height = (event.height - 4 - 40) // 3  # 减去主容器边距和标题高度
        img_size = min(cell_width, cell_height) // 5
        img_size = max(16, img_size)  # 最小图片尺寸16px，避免过小
        # 更新图片大小
        self.update_image_size(img_size, img_size)
        # 强制刷新所有按钮的grid配置，确保sticky="nsew"生效
        for widget in self.grid_panel.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.grid_configure(sticky="nsew")

    # ========== 功能逻辑 ==========
    def create_new_window(self):
        """新建普通弹窗"""
        new_win = tk.Toplevel(self.root)
        new_win.title("新建窗口")
        new_win.geometry("300x200")
        ttk.Label(new_win, text="这是新建的普通窗口", font=("微软雅黑", 12)).pack(expand=True)

    def image_scale(self):
        # 不要创建新的Tk()实例，而是使用Toplevel作为子窗口
        _root = tk.Toplevel()  # 改为Toplevel，继承主窗口的事件循环
        ImageScaleApp(_root)
        # 确保子窗口正确显示
        _root.mainloop()  # 如果需要独立运行子窗口的事件循环

    def image_split(self):
        _root = tk.Toplevel()  # 改为Toplevel，继承主窗口的事件循环
        ImageSplitterApp(_root)
        _root.mainloop()

    def image_qrcode_detect(self):
        messagebox.showinfo("提示", "检测二维码功能已触发！")

    def video_remove_watermark(self):
        messagebox.showinfo("提示", "视频移除水印功能已触发！")

    def video_extract_text(self):
        messagebox.showinfo("提示", "视频提取文字功能已触发！")


if __name__ == "__main__":
    root = tk.Tk()
    app = NormalApp(root)
    root.mainloop()
