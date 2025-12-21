import sys

import cv2
import numpy as np
import os
import tempfile
from pydub import AudioSegment
from tqdm import tqdm

from config import logo_path
from file.file_utils import get_non_hidden_files_video
from pathlib import Path


class VideoProcessor:
    def __init__(self, input_video, logo_path, watermark_size=(150, 150)):
        """
        初始化视频处理器
        :param input_video: 输入视频路径
        :param logo_path: 要添加的logo路径
        :param watermark_size: 水印大小 (宽度, 高度)，默认150x150
        """
        self.input_path = input_video
        self.logo_path = logo_path
        self.watermark_size = watermark_size

        # 自动生成输出文件名
        self.output_path = self._generate_output_path(input_video)

        # 验证输入文件
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"输入视频不存在：{input_video}")
        if not os.path.exists(logo_path):
            raise FileNotFoundError(f"Logo文件不存在：{logo_path}")

        # 临时文件
        self.temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        self.temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name

        # 初始化视频读取器
        self.cap = cv2.VideoCapture(input_video)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频文件：{input_video}")

        # 获取视频信息
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if self.fps <= 0 or self.width <= 0 or self.height <= 0 or self.total_frames <= 0:
            raise RuntimeError("读取的视频信息无效，可能是文件损坏")

        # 计算右上角水印区域
        if self.watermark_size is None:
            self.watermark_region = None
        else:
            self.watermark_region = self._calculate_corner_watermark_region()
            print(f"自动计算右上角水印区域：x={self.watermark_region[0]}, y={self.watermark_region[1]}, "
                  f"宽={self.watermark_region[2]}, 高={self.watermark_region[3]}")

        # 加载并处理logo
        self.logo = self._prepare_logo()

    def _generate_output_path(self, input_path):
        """自动生成输出路径：在原文件名后添加"_logo"后缀"""
        file_dir, file_name = os.path.split(input_path)
        base_name, ext = os.path.splitext(file_name)
        return os.path.join(file_dir, f"{base_name}_logo{ext}")

    def _calculate_corner_watermark_region(self):
        """计算右上角水印区域，留出一定边距"""
        margin = 10  # 边距像素
        w, h = self.watermark_size

        # 确保水印大小不会超出视频尺寸
        w = min(w, self.width - 2 * margin)
        h = min(h, self.height - 2 * margin)

        # 右上角坐标计算
        x = self.width - w - margin
        y = margin

        return (x, y, w, h)

    def _prepare_logo(self):
        """加载logo并调整为固定大小128x128"""
        logo = cv2.imread(self.logo_path, cv2.IMREAD_UNCHANGED)
        if logo is None:
            raise RuntimeError(f"无法读取logo文件：{self.logo_path}")

        # 调整logo大小为128x128
        return cv2.resize(logo, (128, 128), interpolation=cv2.INTER_AREA)

    def add_logo_to_frame(self, frame):
        """在帧的右下角添加logo"""
        # 计算logo放置位置（右下角，留出10像素边距）
        logo_height, logo_width = self.logo.shape[:2]
        x = self.width - logo_width - 10  # 右边距10像素
        y = self.height - logo_height - 10  # 下边距10像素（关键修改点）

        # 处理透明logo
        if self.logo.shape[-1] == 4:
            logo_rgb = self.logo[:, :, :3]
            alpha_mask = self.logo[:, :, 3] / 255.0
            frame_region = frame[y:y + logo_height, x:x + logo_width]

            for c in range(3):
                frame_region[:, :, c] = (alpha_mask * logo_rgb[:, :, c] +
                                         (1 - alpha_mask) * frame_region[:, :, c]).astype(np.uint8)

            frame[y:y + logo_height, x:x + logo_width] = frame_region
        else:
            frame[y:y + logo_height, x:x + logo_width] = self.logo

        return frame

    def remove_watermark_from_frame(self, frame):
        """去除右上角水印"""
        if frame is None:
            raise ValueError("输入帧为空，无法处理")

        # 修复水印区域
        if self.watermark_region is not None:
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                raise ValueError(f"无效的帧格式，需要3通道彩色图像，实际为{frame.shape}")
            x, y, w, h = self.watermark_region

            # 创建掩码
            mask = np.zeros((self.height, self.width), dtype=np.uint8)
            mask[y:y + h, x:x + w] = 255
            repaired_frame = cv2.inpaint(
                src=frame,
                inpaintMask=mask,
                inpaintRadius=3,
                flags=cv2.INPAINT_TELEA
            )
        else:
            repaired_frame = frame

        # 添加logo
        return self.add_logo_to_frame(repaired_frame)

    def extract_audio_from_video(self):
        print("提取音频中...")
        try:
            duration = self.total_frames / self.fps
            audio = AudioSegment.from_file(self.input_path)
            audio = audio[:int(duration * 1000)]
            audio.export(self.temp_audio, format="mp3")
        except Exception as e:
            raise RuntimeError(f"音频提取失败：{str(e)}")

    def process_video_frames(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            self.temp_video,
            fourcc,
            self.fps,
            (self.width, self.height),
            isColor=True
        )

        if not out.isOpened():
            raise RuntimeError("无法创建临时视频文件")

        print(f"处理{self.total_frames}帧中...")
        processed_frames = 0
        with tqdm(total=self.total_frames, unit="帧") as pbar:
            while processed_frames < self.total_frames:
                ret, frame = self.cap.read()
                if not ret:
                    break

                try:
                    processed_frame = self.remove_watermark_from_frame(frame)
                    out.write(processed_frame)
                except Exception as e:
                    raise RuntimeError(f"处理第{processed_frames}帧失败：{str(e)}")

                processed_frames += 1
                pbar.update(1)

        out.release()
        self.cap.release()
        print(f"处理完成{processed_frames}帧")

    def merge_video_and_audio(self):
        print(f"合并音视频中，输出文件：{self.output_path}")
        ffmpeg_cmd = (
            f"ffmpeg -y -i {self.temp_video} -i {self.temp_audio} "
            f"-c:v copy -c:a aac -shortest {self.output_path}"
        )
        exit_code = os.system(ffmpeg_cmd)
        if exit_code != 0:
            raise RuntimeError("音视频合并失败，请检查ffmpeg")

    def clean_temp_files(self):
        for temp_file in [self.temp_video, self.temp_audio]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    print(f"警告：无法删除临时文件{temp_file}")

    def run(self):
        try:
            print(f"输入视频：{self.input_path}")
            print(f"输出视频：{self.output_path}")
            self.extract_audio_from_video()
            self.process_video_frames()
            self.merge_video_and_audio()
            print(f"处理完成！输出文件已保存至：{self.output_path}")
        except Exception as e:
            print(f"处理失败：{str(e)}")
        finally:
            self.clean_temp_files()


if __name__ == "__main__":
    # 示例用法
    INPUT_VIDEO = "/Users/tyrtao/QcHelper/电商/video/文教文化用品/学习用品/橡皮擦/得力71065"  # 带水印的原始视频
    WATERMARK_SIZE = (212, 66)  # 水印大小，可根据实际情况调整

    try:
        file_cache = get_non_hidden_files_video(INPUT_VIDEO)
        if not file_cache:
            print('=======未发现任何文件=======')
            sys.exit(0)

        for file_path in file_cache:
            try:
                print('正在处理视频文件:', file_path)
                processor = VideoProcessor(file_path, logo_path, watermark_size=None)
                processor.run()

            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
    except ValueError as e:
        print(e)
