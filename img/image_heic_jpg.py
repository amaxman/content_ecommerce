"""
主要用于将iOS HEIC图片转换为jpg格式
"""

import os
import cv2
import numpy as np

from config import img_folder_path
from file.file_utils import get_non_hidden_files_pathlib

from pathlib import Path
from PIL import Image
import pillow_heif


def convert_heic_to_jpg(heic_path, jpg_path=None, quality=95):
    """
    将HEIC格式图片转换为JPG格式

    参数:
        heic_path (str): HEIC图片的路径
        jpg_path (str, optional): 输出JPG图片的路径，默认为原路径相同位置
        quality (int, optional): JPG图片质量，范围1-95，默认为95
    """
    try:
        # 确保输入文件存在
        if not os.path.exists(heic_path):
            raise FileNotFoundError(f"文件不存在: {heic_path}")

        # 如果未指定输出路径，则在原路径生成同名JPG文件
        if jpg_path is None:
            # 分离文件名和扩展名
            file_name, _ = os.path.splitext(heic_path)
            jpg_path = f"{file_name}.jpg"

        # 读取HEIC文件
        heif_file = pillow_heif.read(heic_path)

        # 处理不同版本的API差异
        if isinstance(heif_file, list):
            # 某些版本返回图像列表
            image_data = heif_file[0]
        else:
            # 另一些版本直接返回图像数据
            image_data = heif_file

        # 将HEIC转换为PIL Image对象
        image = Image.frombytes(
            image_data.mode,
            image_data.size,
            image_data.data,
            "raw",
            image_data.mode,
            image_data.stride,
        )

        # 保存为JPG格式
        image.save(jpg_path, "JPEG", quality=quality)
        print(f"转换成功: {jpg_path}")
        return True

    except AttributeError as ae:
        # 处理不同版本的API差异
        try:
            # 尝试另一种获取图像数据的方式
            heif_file = pillow_heif.HeifFile(heic_path)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
            image.save(jpg_path, "JPEG", quality=quality)
            print(f"转换成功: {jpg_path}")
            return True
        except Exception as e:
            print(f"转换失败: {str(e)}")
            return False
    except Exception as e:
        print(f"转换失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 指定目录路径
    target_directory = img_folder_path  # 替换为你的目录路径

    try:
        # 获取并缓存文件列表
        file_cache = get_non_hidden_files_pathlib(target_directory)
        total_files = len(file_cache)
        img_file_index = 0

        # 打印缓存结果
        print(f"发现 {len(file_cache)} 个文件路径：")
        for file_path in file_cache:
            try:
                path = Path(file_path)
                file_fold = path.parent
                file_name = path.stem
                jpeg_file_path = os.path.join(file_fold, f"{file_name}.jpg")
                print(f'{jpeg_file_path}')
                if convert_heic_to_jpg(file_path, jpg_path=jpeg_file_path, quality=95):
                    os.remove(file_path)

            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
            finally:
                # print('=======结束=======')
                img_file_index += 1
                print(f'{img_file_index}/{total_files},已完成{img_file_index * 100 / total_files:.2f}%%:{file_path}')

    except ValueError as e:
        print(e)
