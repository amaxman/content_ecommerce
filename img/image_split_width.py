"""
将制定图片按照宽度切为N等分
"""

import os
import cv2
import numpy as np

from config import img_folder_path
from file.file_utils import get_non_hidden_files_deli_xq

from pathlib import Path
from file.file_utils import get_non_hidden_files_video


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


def split_image_by_width(img, num_parts):
    """
    按照宽度将图片平均切分成指定数量的部分

    参数:
        img: OpenCV读取的图像
        num_parts: 要切分的部分数量

    返回:
        切分后的图像列表
    """
    if num_parts <= 0:
        raise ValueError("切分数量必须大于0")

    # 获取图像的高度和宽度
    height, width = img.shape[:2]

    # 计算每一部分的宽度
    part_width = width // num_parts

    # 存储切分后的图像
    split_images = []

    # 切分图像
    for i in range(num_parts):
        # 计算当前部分的起始和结束列
        start_col = i * part_width
        # 最后一部分可能需要处理余数，确保覆盖整个宽度
        end_col = (i + 1) * part_width if i < num_parts - 1 else width

        # 提取当前部分
        part = img[:, start_col:end_col]
        split_images.append(part)

    return split_images


def split_image_into_squares(img, total, output_dir, file_name):
    """
    将图片上下拆分为正方形片段，使用图片宽度作为每个片段的高度

    参数:
        img: cv2读取的图片数组
        output_dir: 输出目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    try:
        split_images = split_image_by_width(img, total)
        for i in range(len(split_images)):
            image = split_images[i]
            output_path = os.path.join(output_dir, f"{file_name}_{i + 1:02d}.png")
            cv2.imwrite(output_path, image)

    except Exception as e:
        print(f"处理图片时出错: {str(e)}")


def split_image(input_path, total):
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

        new_path = path.parent
        split_image_into_squares(img_cv, total, new_path, path.stem)



    except Exception as e:
        print(f"处理图片时出错: {str(e)}")
        return False


if __name__ == "__main__":
    # 指定图片路径
    target_directory = '/Users/tyrtao/QcHelper/电商/素材/店铺门头.jpg'  # 替换为你的目录路径
    if not os.path.exists(target_directory):
        exit(0)

    # region 获取文件宽度
    try:
        split_image(target_directory, 3)

    except Exception as e:
        print(f"处理图片时出错: {str(e)}")
    # endregion
