import os
from pathlib import Path
import cv2
import numpy as np


def get_non_hidden_files_pathlib(directory):
    """使用pathlib获取目录中所有非隐藏文件"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效的目录: {directory}")

    # 过滤掉所有以.开头的文件和目录
    return [str(file) for file in dir_path.rglob('*')
            if file.is_file()
            and not any(part.startswith('.') for part in file.parts)]


def get_non_hidden_files_deli_xq(directory):
    """使用pathlib获取目录中所有非隐藏文件"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效的目录: {directory}")

    # 过滤掉所有以.开头的文件和目录
    return [str(file) for file in dir_path.rglob('*')
            if file.is_file()
            and file.stem.lower() == 'xq'
            and not any(part.startswith('.') for part in file.parts)]


def get_non_hidden_files_video(directory):
    """使用pathlib获取目录中所有非隐藏文件"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效的目录: {directory}")

    # 过滤掉所有以.开头的文件和目录
    return [str(file) for file in dir_path.rglob('*.mp4')
            if file.is_file()
            and file.suffix.lower() == '.mp4'
            and not any(part.startswith('.') for part in file.parts)]


def get_hidden_files(directory):
    """使用pathlib获取目录中所有非隐藏文件"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效的目录: {directory}")

    return [str(file) for file in dir_path.rglob('*')
            if file.is_file()
            and any(part.startswith('.') for part in file.parts)]


def read_chinese_path_image(image_path):
    """读取包含中文的图片路径"""
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}")
        return None

    # 使用numpy读取文件，再用OpenCV解码
    try:
        # 以二进制模式读取文件
        file_data = np.fromfile(image_path, dtype=np.uint8)
        # 解码图片
        img = cv2.imdecode(file_data, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"读取失败: {e}")
        return None


def cv2_imwrite_chinese(output_path, image):
    """
    支持中文路径的cv2.imwrite替代函数

    Args:
        output_path: 保存路径（可包含中文）
        image: 要保存的OpenCV图像数组

    Returns:
        bool: 保存成功返回True，失败返回False
    """
    try:
        # 获取文件扩展名
        if '.' in output_path:
            ext = '.' + output_path.split('.')[-1]
        else:
            ext = '.jpg'  # 默认使用jpg格式

        # 根据扩展名设置编码参数
        encode_params = []
        if ext.lower() in ['.jpg', '.jpeg']:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        elif ext.lower() == '.png':
            encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 0]

        # 编码图像并保存
        retval, im_buf_arr = cv2.imencode(ext, image, encode_params)

        if retval:
            # 确保目录存在
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # 写入文件
            im_buf_arr.tofile(output_path)
            return True
        else:
            return False

    except Exception as e:
        print(f"保存图片失败: {e}")
        return False

if __name__ == "__main__":
    # 指定目录路径
    target_directory = r'D:\电商'  # 替换为你的目录路径
    file_cache=get_hidden_files(target_directory)

    for file_path in file_cache:
        print(file_path)
        os.remove(file_path)


