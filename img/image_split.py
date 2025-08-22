"""
主要用于淘宝图片切分。按照得力的图片风格，官网下载的xq.jpg无法直接上传到淘宝素材中
"""

import os
import cv2
import numpy as np

from config import img_folder_path
from file.file_utils import get_non_hidden_files_deli_xq

from pathlib import Path


def get_file_new_path(path):
    # 提取文件所在的目录路径
    file_directory = os.path.dirname(path)

    # 提取文件名（包含扩展名）
    file_name = os.path.basename(path)

    # 提取文件名（不包含扩展名）和扩展名
    file_name_without_ext, file_extension = os.path.splitext(file_name)

    new_path = os.path.join(file_directory,
                            file_name_without_ext.replace('扫描全能王 ', '') + '_800x800' + file_extension)

    return new_path


def preprocess_image(img_cv):
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


def blur_qrcode_opencv(img_cv):
    """使用OpenCV识别并模糊图片中的二维码，增加预处理步骤提高识别率"""
    # 创建原始图像的副本用于最终处理
    img_copy = img_cv.copy()

    # 对图像进行预处理以提高识别率
    processed = preprocess_image(img_cv)

    # 初始化QR码检测器
    qr_detector = cv2.QRCodeDetector()

    # 尝试多种方式检测二维码
    detection_methods = [
        # 直接检测原始图像
        (img_cv, "原始图像"),
        # 检测预处理后的图像
        (processed, "预处理图像"),
        # 检测原始图像的灰度版本
        (cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY), "灰度图像")
    ]

    for img, method in detection_methods:
        retval, _, points, _ = qr_detector.detectAndDecodeMulti(img)

        if retval:
            print(f"使用{method}成功识别到二维码")
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
    # print("未检测到二维码")
    return img_copy


def split_image_into_squares(img, output_dir, file_name):
    """
    将图片上下拆分为正方形片段，使用图片宽度作为每个片段的高度

    参数:
        img: cv2读取的图片数组
        output_dir: 输出目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 获取图片尺寸 (高度, 宽度, 通道数)
        height, width = img.shape[:2]
        # print(f"原始图片尺寸: 宽度 {width}px, 高度 {height}px")

        # 使用图片宽度作为每个正方形片段的高度
        segment_height = width
        # print(f"每个正方形片段尺寸: {width}px × {segment_height}px")

        # 计算可以分成多少段
        num_segments = (height + segment_height - 1) // segment_height
        # print(f"将上下拆分为 {num_segments} 个正方形片段")

        # 拆分图片
        for i in range(num_segments):
            # 计算当前分段的起始和结束位置（垂直方向）
            start_y = i * segment_height
            end_y = start_y + segment_height

            # 确保不超过图片高度
            if end_y > height:
                end_y = height

            # 裁剪图片 (OpenCV格式为 [y1:y2, x1:x2])
            # 宽度方向取完整宽度，高度方向取当前分段
            segment = img[start_y:end_y, :width]

            # 生成输出文件名
            output_path = os.path.join(output_dir, f"{file_name}_{i + 1}.png")

            # 保存分段图片
            cv2.imwrite(output_path, segment)


    except Exception as e:
        print(f"处理图片时出错: {str(e)}")


def resize_image(input_path):
    path = Path(input_path)
    if not path.exists():
        return False

    if path.is_dir():
        return False

    try:
        # 使用OpenCV读取图片
        img_cv = cv2.imread(input_path)
        if img_cv is None:
            print(f"无法读取图片: {input_path}")
            return False

        # 先识别并模糊原始图片中的二维码
        img_with_blur = blur_qrcode_opencv(img_cv)

        path = Path(file_path)

        new_path = path.parent
        split_image_into_squares(img_with_blur, new_path, path.stem)



    except Exception as e:
        print(f"处理图片时出错: {str(e)}")
        return False


if __name__ == "__main__":
    # 指定目录路径
    target_directory = img_folder_path  # 替换为你的目录路径

    try:
        # 获取并缓存文件列表
        file_cache = get_non_hidden_files_deli_xq(target_directory)
        total_files = len(file_cache)
        img_file_index = 0

        # 打印缓存结果
        print(f"发现 {len(file_cache)} 个文件路径：")
        for file_path in file_cache:
            try:
                resize_image(file_path)

            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
            finally:
                # print('=======结束=======')
                img_file_index += 1
                print(f'{img_file_index}/{total_files},已完成{img_file_index*100/total_files:.2f}%%:{file_path}')

    except ValueError as e:
        print(e)
