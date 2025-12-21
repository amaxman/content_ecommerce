import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageFilter
import os
import datetime


class ImageBlurApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("图片模糊工具")
        self.root.geometry("800x600")  # 初始窗口大小

        # 创建按钮区域
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)

        # 保存按钮
        self.save_btn = tk.Button(
            self.button_frame,
            text="保存处理后的图片",
            command=self.save_image
        )
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        # 重置按钮
        self.reset_btn = tk.Button(
            self.button_frame,
            text="重置模糊区域",
            command=self.reset_blur_regions
        )
        self.reset_btn.pack(side=tk.RIGHT, padx=5)

        # 初始化状态标签
        self.status_label = tk.Label(root, text="准备加载图片...")
        self.status_label.pack(fill=tk.X, padx=5, pady=5)

        try:
            # 打开原始图片
            self.original_image = Image.open(image_path)
            self.original_width, self.original_height = self.original_image.size
            self.image_path = image_path  # 保存原始图片路径

            # 存储模糊区域信息（基于原始图片坐标）
            self.blur_regions = []
            self.max_regions = 3  # 最多3个模糊区域
            self.region_size = (120, 120)  # 模糊区域大小（原始图片尺寸）

            # 创建画布容器（带滚动条）
            self.canvas_frame = tk.Frame(root)
            self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # 创建画布
            self.canvas = tk.Canvas(self.canvas_frame)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # 添加滚动条
            self.scroll_x = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
            self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
            self.scroll_y = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
            self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

            # 关联滚动条和画布
            self.canvas.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
            self.canvas.bind("<Configure>", self.on_canvas_configure)

            # 绑定点击事件和鼠标滚轮缩放
            self.canvas.bind("<Button-1>", self.on_click)
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
            self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux
            self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux

            # 缩放比例
            self.scale_factor = 1.0
            self.min_scale = 0.1
            self.max_scale = 3.0

            # 显示图片
            self.update_display()

        except Exception as e:
            self.status_label.config(text=f"加载图片出错: {str(e)}")
            return

    def on_canvas_configure(self, event):
        """画布大小变化时调整滚动区域"""
        if hasattr(self, 'image_on_canvas'):
            self.canvas.configure(scrollregion=self.canvas.bbox(self.image_on_canvas))

    def on_mouse_wheel(self, event):
        """鼠标滚轮缩放图片"""
        # 计算缩放方向和比例
        if event.num == 4 or event.delta > 0:  # 放大
            new_scale = self.scale_factor * 1.1
        else:  # 缩小
            new_scale = self.scale_factor / 1.1

        # 限制缩放范围
        if self.min_scale <= new_scale <= self.max_scale:
            self.scale_factor = new_scale
            self.update_display()

    def scale_coords(self, x, y):
        """将画布坐标转换为原始图片坐标"""
        return int(x / self.scale_factor), int(y / self.scale_factor)

    def update_display(self):
        """更新画布上显示的图片（包含缩放和模糊处理）"""
        # 先复制原始图片并应用模糊
        temp_image = self.original_image.copy()

        # 对每个区域应用模糊
        for (x, y) in self.blur_regions:
            # 计算模糊区域的坐标（以点击点为中心）
            left = max(0, x - self.region_size[0] // 2)
            top = max(0, y - self.region_size[1] // 2)
            right = min(self.original_width, left + self.region_size[0])
            bottom = min(self.original_height, top + self.region_size[1])

            # 提取区域并模糊
            region = self.original_image.crop((left, top, right, bottom))
            blurred_region = region.filter(ImageFilter.GaussianBlur(radius=10))

            # 将模糊后的区域放回去
            temp_image.paste(blurred_region, (left, top))

        # 应用缩放
        scaled_width = int(self.original_width * self.scale_factor)
        scaled_height = int(self.original_height * self.scale_factor)
        scaled_image = temp_image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

        # 更新显示
        self.display_image = ImageTk.PhotoImage(scaled_image)
        # 清除原有图片并绘制新图片
        self.canvas.delete("all")
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)

        # 更新滚动区域
        self.canvas.configure(scrollregion=self.canvas.bbox(self.image_on_canvas))

        # 更新状态标签
        self.status_label.config(
            text=f"已添加 {len(self.blur_regions)} 个模糊区域（还可添加 {self.max_regions - len(self.blur_regions)} 个） | 缩放: {self.scale_factor:.1f}x"
        )

    def on_click(self, event):
        """处理鼠标点击事件（转换坐标后记录）"""
        if len(self.blur_regions) < self.max_regions:
            # 将画布坐标转换为原始图片坐标
            original_x, original_y = self.scale_coords(event.x, event.y)
            self.blur_regions.append((original_x, original_y))
            self.update_display()
        else:
            self.status_label.config(text=f"已达到最大模糊区域数量（3个） | 缩放: {self.scale_factor:.1f}x")

    def reset_blur_regions(self):
        """重置所有模糊区域"""
        self.blur_regions = []
        self.update_display()
        messagebox.showinfo("重置完成", "所有模糊区域已清除")

    def save_image(self):
        """保存处理后的图片"""
        if not hasattr(self, 'original_image'):
            messagebox.showerror("错误", "没有可保存的图片")
            return

        try:
            # 创建处理后的图片（应用所有模糊）
            processed_image = self.original_image.copy()

            # 应用所有模糊区域
            for (x, y) in self.blur_regions:
                left = max(0, x - self.region_size[0] // 2)
                top = max(0, y - self.region_size[1] // 2)
                right = min(self.original_width, left + self.region_size[0])
                bottom = min(self.original_height, top + self.region_size[1])

                region = self.original_image.crop((left, top, right, bottom))
                blurred_region = region.filter(ImageFilter.GaussianBlur(radius=10))
                processed_image.paste(blurred_region, (left, top))

            # 生成默认保存路径（在原图目录下添加"_blurred"后缀）
            dir_name, file_name = os.path.split(self.image_path)
            base_name, ext = os.path.splitext(file_name)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(dir_name, f"{base_name}_blurred_{timestamp}{ext}")

            # 弹出保存对话框
            # 保存图片
            processed_image.save(save_path)
            messagebox.showinfo("保存成功", f"图片已保存至:\n{save_path}")
            self.status_label.config(text=f"图片已保存至: {save_path}")

        except Exception as e:
            messagebox.showerror("保存失败", f"保存图片时出错:\n{str(e)}")


if __name__ == "__main__":
    # 图片路径
    image_path = '/Users/tyrtao/QcHelper/电商/家庭清洁_纸品/驱蚊驱虫/灭鼠用品/粘鼠板/爱必达/20891/2025-11-1 10.37_3_1024x1024.JPG'

    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"错误：找不到图片文件 {image_path}")
        print("请选择其他图片文件...")
        # 如果文件不存在，让用户选择一个图片
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        image_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        root.destroy()
        if not image_path:
            print("未选择图片，程序退出")
            exit()

    # 启动应用
    root = tk.Tk()
    app = ImageBlurApp(root, image_path)
    root.mainloop()
