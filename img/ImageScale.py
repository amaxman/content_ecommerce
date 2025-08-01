import os
from pathlib import Path
from PIL import Image

from config import img_folder_path, img_width, img_height


def get_non_hidden_files_os(directory):
    """使用os模块获取目录中所有非隐藏文件"""
    file_list = []
    for root, dirs, files in os.walk(directory):
        # 过滤隐藏目录（不遍历以.开头的目录）
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            # 过滤隐藏文件
            if not file.startswith('.'):
                file_path = os.path.join(root, file)
                file_list.append(file_path)
    return file_list


def get_non_hidden_files_pathlib(directory):
    """使用pathlib获取目录中所有非隐藏文件"""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"目录不存在或不是有效的目录: {directory}")

    # 过滤掉所有以.开头的文件和目录
    return [str(file) for file in dir_path.rglob('*')
            if file.is_file()
            and not any(part.startswith('.') for part in file.parts)]


def resize_image(input_path, output_path):
    """
    将图片调整为800x800尺寸，保持原比例，空白处用白色填充

    参数:
        input_path: 输入图片路径
        output_path: 输出图片路径
    """
    # 打开原始图片
    with Image.open(input_path) as img:
        # 获取原始图片的宽和高
        width, height = img.size

        if width == img_width and height == img_height:
            return False

        # 计算缩放系数
        if width > height:
            # 长度(宽度)大于宽度(高度)，使用宽度作为缩放系数
            scale = img_width / width
        else:
            # 宽度大于等于长度，使用高度作为缩放系数
            scale = img_height / height

        # 计算缩放后的尺寸
        new_width = int(width * scale)
        new_height = int(height * scale)

        # 缩放图片
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 创建800x800的白色背景图片
        new_img = Image.new('RGB', (img_width, img_height), (255, 255, 255))

        # 计算粘贴位置（居中放置）
        paste_x = (img_width - new_width) // 2
        paste_y = (img_height - new_height) // 2

        # 将缩放后的图片粘贴到白色背景上
        new_img.paste(resized_img, (paste_x, paste_y))

        # 保存结果图片
        new_img.save(output_path)

        return True


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
        for file_path in file_cache:  # 只打印前5个文件
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
