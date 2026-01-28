import os
import sys
from pathlib import Path

from config import video_target_path, wav_text_path
from file.file_utils import get_non_hidden_files_video

from moviepy.video.io.VideoFileClip import VideoFileClip  # 直接导入视频处理类
import speech_recognition as sr

import whisper
import warnings

import cv2
import easyocr
import time
from datetime import timedelta


def mp4_to_text(mp4_path, model):
    """
    将MP4视频文件转换为文本（修复moviepy导入问题）
    """
    # 检查文件是否存在
    if not os.path.exists(mp4_path) or not mp4_path.lower().endswith('.mp4'):
        raise ValueError("请提供有效的MP4文件路径")

    try:
        # 1. 提取音频（使用直接导入的VideoFileClip）
        _mp4_path = Path(mp4_path)
        with VideoFileClip(mp4_path) as video:  # 使用with语句确保资源正确释放
            audio = video.audio

            # 保存为临时WAV文件
            temp_audio_path = os.path.join(_mp4_path.parent, _mp4_path.stem + ".wav")
            audio.write_audiofile(temp_audio_path, logger=None)

        # 2. 音频转文本
        print("正在将音频转换为文本...", temp_audio_path)

        result = model.transcribe(
            temp_audio_path
            , language="zh"
            , fp16=False,  # 避免MPS/CPU的FP16兼容问题
            initial_prompt="以下是简体中文的语音内容，识别结果请使用简体中文输出，避免使用繁体字。",  # 提示模型优先简体
            verbose=False  # 关闭转录过程中的冗余日志（如"Detected language: zh"）
        )  # 指定中文
        text = result["text"]

        # 清理临时文件
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        return text

    except sr.UnknownValueError:
        return "无法识别音频内容"
    except sr.RequestError as e:
        return f"语音识别服务请求失败: {e}"
    except Exception as e:
        return f"处理过程出错: {str(e)}"


def load_whisper_with_mps(model_path_or_size="base"):
    """
    兼容所有Python版本：解决MPS稀疏张量错误 + 消除FP16警告
    """

    # ------------------- 修复1：兼容Python版本的警告过滤 -------------------
    # 直接根据警告字符串内容过滤，不依赖WarningMessage的message属性
    def filter_fp16_warning(message, category, filename, lineno, file=None, line=None):
        # 仅过滤"FP16 is not supported on CPU; using FP32 instead"警告
        if "FP16 is not supported on CPU; using FP32 instead" in str(message):
            return  # 忽略该警告
        # 其他警告正常显示
        warnings.showwarning(message, category, filename, lineno, file, line)

    # 替换默认的警告显示函数
    warnings.showwarning = filter_fp16_warning

    # ------------------- 修复2：MPS稀疏张量问题 -------------------
    # 检测MPS可用性
    # if not torch.backends.mps.is_available():
    print("未检测到MPS支持，使用CPU运行")
    device = "cpu"
    model = whisper.load_model(model_path_or_size, device=device)
    return model

    # print("检测到MPS支持，禁用稀疏张量以适配GPU")
    # device = "mps"
    #
    # # 1. 先在CPU加载模型（避免MPS直接加载稀疏张量报错）
    # model = whisper.load_model(model_path_or_size, device="cpu")
    #
    # # 2. 稀疏张量转密集张量（绕过MPS不支持的操作）
    # for name, module in model.named_modules():
    #     # 处理模型权重
    #     if hasattr(module, "weight") and isinstance(module.weight, torch.Tensor):
    #         if module.weight.is_sparse:
    #             module.weight = torch.nn.Parameter(module.weight.to_dense())
    #     # 处理模型缓冲（如语言模型的偏置项）
    #     for buf_name, buf in module.named_buffers():
    #         if isinstance(buf, torch.Tensor) and buf.is_sparse:
    #             setattr(module, buf_name, buf.to_dense())
    #
    # # 3. 迁移模型到MPS设备
    # model = model.to(device)
    # return model


def save_text_to_file(file_path, text):
    if file_path is None or text is None or text == '':
        return
    if len(text) <= 20:
        return
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"文本已保存至: {file_path}")


def video_text_recognition(video_path, lang=['ch_sim', 'en']):
    """
    使用EasyOCR识别视频中的文字
    :param video_path: 视频文件路径
    :param lang: 识别语言（中文简体+英文）
    """
    results = []
    # 1. 初始化EasyOCR阅读器（首次运行会下载模型，约1GB）
    # 若需离线使用，提前下载模型：https://github.com/JaidedAI/EasyOCR/blob/master/README.md#model-download
    reader = easyocr.Reader(lang
                            , model_storage_directory='/Users/tyrtao/AI/文字识别/easyOCR'  # 你的模型存放目录
                            , download_enabled=False  # 禁用自动下载,
                            , gpu=False
                            )  # 若有GPU可设为True

    # 2. 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"无法打开视频：{video_path}")
        return results

    # 3. 视频基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps  # 视频总时长（秒）
    print(f"视频信息：时长{duration:.1f}秒，帧率{fps:.1f}")

    # 4. 关键优化参数（根据视频特性调整）
    sample_interval = max(1, int(fps * 1.5))  # 每1.5秒采样一帧（动态适配帧率）
    max_size = 640  # 图像最大边长（超过则压缩，平衡精度和速度）
    seen_texts = set()  # 去重集合

    start_time = time.time()
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        try:
            # 按时间间隔采样（而非固定帧数，适配不同帧率视频）
            if frame_count % sample_interval == 0:
                # 优化1：压缩图像（降低分辨率）
                h, w = frame.shape[:2]
                if max(h, w) > max_size:
                    scale = max_size / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                # 优化2：转为灰度图（减少计算量，不影响OCR精度）
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # 执行识别（仅返回文字和置信度）
                ocr_result = reader.readtext(frame_gray, detail=1)

                # 提取有效文字（过滤低置信度）
                for _, text, score in ocr_result:
                    if score > 0.6 and text.strip():  # 提高置信度阈值，减少无效计算
                        text_clean = text.strip().lower()
                        if text_clean not in seen_texts:
                            seen_texts.add(text_clean)
                            results.append(text.strip())
                            print(f"识别到：{text.strip()}")
        except Exception as e:
            print(e)
        finally:
            frame_count += 1

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()

    # 性能统计
    end_time = time.time()
    print(f"\n处理完成！耗时{end_time - start_time:.2f}秒")
    print(f"采样帧数：{frame_count // sample_interval} / {total_frames}")
    print(f"去重后结果数：{len(results)}")
    return results


def split_wav(mp4_path):
    """
    提取MP4视频文件中的音频文件
    """
    """
    将MP4视频文件转换为文本（修复moviepy导入问题）
    """
    # 检查文件是否存在
    if not os.path.exists(mp4_path) or not mp4_path.lower().endswith('.mp4'):
        raise ValueError("请提供有效的MP4文件路径")

    try:
        # 1. 提取音频（使用直接导入的VideoFileClip）
        _mp4_path = Path(mp4_path)
        with VideoFileClip(mp4_path) as video:  # 使用with语句确保资源正确释放
            audio = video.audio

            # 保存为临时WAV文件
            temp_audio_path = os.path.join(_mp4_path.parent, _mp4_path.stem + ".wav")
            audio.write_audiofile(temp_audio_path, logger=None)

        print("音频文件路径:", temp_audio_path)


    except sr.UnknownValueError:
        return "无法识别音频内容"
    except sr.RequestError as e:
        return f"语音识别服务请求失败: {e}"
    except Exception as e:
        return f"处理过程出错: {str(e)}"


if __name__ == "__main__":
    # split_wav('/Users/tyrtao/QcHelper/电商/店铺宣传视频/2025年秋/2025秋促销竖屏.mp4')
    target_path = Path(video_target_path)
    if not target_path.exists():
        sys.exit(0)
    if not target_path.is_dir():
        print(target_path + '不是目录')
        sys.exit(0)

    model = load_whisper_with_mps("/Users/tyrtao/AI/文字识别/语音识别/whisper/medium.pt")

    try:
        file_cache = get_non_hidden_files_video(target_path)
        if not file_cache:
            print('=======未发现任何文件=======')
            sys.exit(0)

        for file_path in file_cache:
            try:
                print('正在处理视频文件:', file_path)
                path = Path(file_path)

                text = mp4_to_text(file_path, model)
                print('语音识别结果:', text)

                results = video_text_recognition(file_path)
                print('视频识别结果:', text)

                save_text_to_file(os.path.join(path.parent, path.stem + '.txt'), text + '\r\n' + '\r\n'.join(results))

            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
    except ValueError as e:
        print(e)
