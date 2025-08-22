import os
import cv2
import numpy as np

from config import img_folder_path, img_width, img_height
from file.file_utils import get_non_hidden_files_pathlib


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
    print("未检测到二维码")
    return img_copy


def resize_image(input_path, output_path):
    """先处理二维码，再根据长宽比旋转（长度>宽度时旋转90度），最后调整图片大小"""
    try:
        # 使用OpenCV读取图片
        img_cv = cv2.imread(input_path)
        if img_cv is None:
            print(f"无法读取图片: {input_path}")
            return False

        # 先识别并模糊原始图片中的二维码
        img_with_blur = blur_qrcode_opencv(img_cv)

        # 获取处理后的图片的宽和高
        height, width = img_with_blur.shape[:2]

        # 如果长度（高度）小于宽度，则旋转90度
        rotated = False
        if height < width:
            print(f"图片长度({height})大于宽度({width})，旋转90度")
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
        cv2.imwrite(output_path, new_img)

        return True

    except Exception as e:
        print(f"处理图片时出错: {str(e)}")
        return False


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


if __name__ == "__main__":
    # 指定目录路径
    target_directory = img_folder_path  # 替换为你的目录路径

    try:
        # 获取并缓存文件列表
        file_cache = get_non_hidden_files_pathlib(target_directory)

        # 打印缓存结果
        print(f"发现 {len(file_cache)} 个文件路径：")
        for file_path in file_cache:
            try:
                print('=======开始=======\r\n', file_path)
                if '_800x800' in file_path:
                    print('文件名忽略')
                    continue

                new_path = get_file_new_path(file_path)
                result = resize_image(file_path, new_path)
                if result:
                    os.remove(file_path)
                    print('删除文件', file_path)
            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
            finally:
                print('=======结束=======')

    except ValueError as e:
        print(e)
