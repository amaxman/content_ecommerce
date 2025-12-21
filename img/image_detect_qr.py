"""
通过图片检测二维码并显示
"""
import os
# 添加 zbar 库路径到环境变量
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get("DYLD_LIBRARY_PATH", "")

import cv2
from pyzbar.pyzbar import decode
import numpy as np


def detect_qr_in_image(image_path):
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法读取图片: {image_path}")
        return

    # 检测并解码二维码
    qr_codes = decode(image)

    if not qr_codes:
        print("未检测到二维码")
        # 显示原图
        cv2.imshow("二维码检测结果", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # 处理每个检测到的二维码
    for qr_code in qr_codes:
        # 提取二维码边界框坐标
        points = qr_code.polygon
        if len(points) == 4:
            # 转换为整数坐标并绘制多边形边框（绿色）
            pts = np.array([[p.x, p.y] for p in points], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(image, [pts], True, (0, 255, 0), 2)

        # 获取二维码内容并显示
        qr_data = qr_code.data.decode('utf-8')  # 解码内容
        qr_type = qr_code.type  # 二维码类型（如QRCODE）
        # 在图片上绘制文本（红色）
        cv2.putText(
            image,
            f"{qr_type}: {qr_data}",
            (qr_code.rect.left, qr_code.rect.top - 10),  # 文本位置（二维码上方）
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,  # 字体大小
            (0, 0, 255),  # 红色
            2  # 线条粗细
        )
        # 打印到控制台
        print(f"检测到{qr_type}：{qr_data}")

    # 显示标注后的图片
    cv2.imshow("二维码检测结果", image)
    cv2.waitKey(0)  # 等待按键关闭窗口
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # 替换为你的图片路径（支持.jpg/.png等格式）
    image_path = "/Users/tyrtao/QcHelper/电商/家庭清洁_纸品/驱蚊驱虫/灭鼠用品/粘鼠板/爱必达/20884/2025-11-1 10.37_1_1024x1024.JPG"
    detect_qr_in_image(image_path)
