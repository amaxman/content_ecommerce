from pathlib import Path


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
