import os
import sys
from pathlib import Path

from config import video_target_path, video_path
from file.file_utils import get_non_hidden_files_video


def move_file(root_path, src_path, target_fold):
    _src_path = Path(src_path)
    if not _src_path.exists():
        return
    if _src_path.is_dir():
        return
    _target_fold = Path(target_fold)
    relative_file_path = _src_path.relative_to(root_path)
    print('相对路径:', relative_file_path)
    new_path = os.path.join(target_fold, relative_file_path)
    print('最新路径:', new_path)
    _new_path = Path(new_path)
    if _new_path.is_dir():
        return
    if _new_path.exists():
        return
    if not _new_path.parent.exists():
        os.makedirs(_new_path.parent)
    print('准备移动文件:', src_path, '==>', new_path)
    _src_path.rename(new_path)


if __name__ == "__main__":
    video_path = Path(video_path)
    target_path = Path(video_target_path)
    if not video_path.exists():
        sys.exit(0)
    if not video_path.is_dir():
        print(video_path + '不是目录')
        sys.exit(0)
    if not target_path.exists():
        target_path.mkdir()

    try:
        file_cache = get_non_hidden_files_video(video_path)
        if not file_cache:
            print('=======未发现任何文件=======')
            sys.exit(0)

        for file_path in file_cache:
            try:
                move_file(video_path, file_path, target_path)

            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
            finally:
                print('=======结束=======')
    except ValueError as e:
        print(e)
