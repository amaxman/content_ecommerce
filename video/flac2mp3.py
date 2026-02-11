import os

import ffmpeg


def convert_audio_to_mp3(input_path, output_path, bitrate="320k"):
    """
    将 flac/ogg 音频转换为 mp3 格式

    Args:
        input_path (str): 输入音频文件路径（flac/ogg）
        output_path (str): 输出 mp3 文件路径
        bitrate (str): mp3 比特率，默认 320k（高质量）
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在：{input_path}")

        # 检查输出目录是否存在，不存在则创建
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 使用 ffmpeg 转换格式
        (
            ffmpeg
            .input(input_path)
            .output(output_path, audio_bitrate=bitrate)
            .overwrite_output()  # 覆盖已存在的输出文件
            .run(quiet=True)  # 静默运行，不输出冗余日志
        )
        print(f"✅ 转换成功：{input_path} -> {output_path}")

    except Exception as e:
        print(f"❌ 转换失败：{input_path}，错误：{str(e)}")


def batch_convert_folder(input_folder, output_folder, bitrate="320k"):
    """
    批量转换文件夹下的所有 flac/ogg 文件为 mp3

    Args:
        input_folder (str): 输入文件夹路径
        output_folder (str): 输出文件夹路径
        bitrate (str): mp3 比特率
    """
    # 支持的输入格式
    supported_formats = (".flac", ".ogg")

    # 遍历文件夹下的所有文件
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            # 筛选出 flac/ogg 文件
            if file.lower().endswith(supported_formats):
                # 构建输入路径
                input_path = os.path.join(root, file)
                # 构建输出路径（保持原文件目录结构）
                relative_path = os.path.relpath(input_path, input_folder)
                output_path = os.path.join(output_folder, relative_path)
                # 替换文件后缀为 mp3
                output_path = os.path.splitext(output_path)[0] + ".mp3"

                # 执行转换
                convert_audio_to_mp3(input_path, output_path, bitrate)


def convert_audio(input_target, output_folder, bitrate="320k"):
    """
    统一入口函数：自动判断输入是文件还是目录，执行对应转换逻辑

    Args:
        input_target (str): 输入路径（文件或目录）
        output_folder (str): 输出目录路径
        bitrate (str): mp3 比特率
    """
    # 检查输入路径是否存在
    if not os.path.exists(input_target):
        print(f"❌ 输入路径不存在：{input_target}")
        return

    # 判断是文件还是目录
    if os.path.isfile(input_target):
        # 处理单个文件
        file_name = os.path.basename(input_target)
        # 检查文件格式是否支持
        if not file_name.lower().endswith((".flac", ".ogg")):
            print(f"❌ 不支持的文件格式：{input_target}（仅支持 flac/ogg）")
            return
        # 构建输出文件路径
        output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + ".mp3")
        convert_audio_to_mp3(input_target, output_path, bitrate)
    elif os.path.isdir(input_target):
        # 处理目录（批量转换）
        batch_convert_folder(input_target, output_folder, bitrate)
    else:
        print(f"❌ 无效的输入路径：{input_target}")


# 示例使用（适配你的路径）
if __name__ == "__main__":
    # 配置你的路径
    INPUT_TARGET = "/Users/tyrtao/tools/music/src"  # 可以是文件路径（如 "/Users/tyrtao/tools/music/src/test.flac"）或目录路径
    OUTPUT_FOLDER = "/Users/tyrtao/tools/music/dest"  # 固定为输出目录
    BITRATE = "320k"  # 音质可选：128k/192k/320k

    # 执行转换（自动识别输入类型）
    convert_audio(INPUT_TARGET, OUTPUT_FOLDER, BITRATE)

    # 单独测试单个文件的示例（取消注释即可）
    # convert_audio("/Users/tyrtao/tools/music/src/xxx.ogg", OUTPUT_FOLDER)
    # convert_audio("/Users/tyrtao/tools/music/src/yyy.flac", OUTPUT_FOLDER)
