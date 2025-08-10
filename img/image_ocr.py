import easyocr
import os
import numpy as np
from collections import defaultdict


def recognize_table_with_easyocr(image_path):
    """识别表格图片并尝试还原表格结构"""
    try:
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            print(f"错误：图片文件不存在 - {image_path}")
            return None

        # 初始化阅读器
        reader = easyocr.Reader(['ch_sim', 'en']
                                , model_storage_directory='/Users/tyrtao/AI/文字识别/easyOCR'  # 你的模型存放目录
                                , download_enabled=False  # 禁用自动下载,
                                , gpu=False)

        # 执行识别，获取带坐标的结果
        # result格式: [([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], '文本', 置信度), ...]
        result = reader.readtext(image_path)

        if not result:
            print("未识别到任何内容")
            return None

        # 提取所有文本的y坐标（用于判断行）
        y_coordinates = [item[0][0][1] for item in result]

        # 聚类y坐标，确定行（通过阈值判断是否为同一行）
        rows = cluster_coordinates(y_coordinates, threshold=15)

        # 按行分组文本
        row_items = defaultdict(list)
        for i, item in enumerate(result):
            coords, text, _ = item
            # 找到当前项所属的行
            for row_idx, y_range in rows.items():
                if y_range[0] <= coords[0][1] <= y_range[1]:
                    row_items[row_idx].append((coords[0][0], text))  # (x坐标, 文本)
                    break

        # 对每行按x坐标排序（确定列顺序）
        table_data = []
        for row_idx in sorted(row_items.keys()):
            # 按x坐标排序，确保列顺序正确
            sorted_items = sorted(row_items[row_idx], key=lambda x: x[0])
            # 提取文本
            row_text = [text for (x, text) in sorted_items]
            table_data.append(row_text)

        return table_data

    except Exception as e:
        print(f"识别过程出错：{str(e)}")
        return None


def cluster_coordinates(coordinates, threshold=10):
    """将相近的坐标聚类（用于识别行）"""
    if not coordinates:
        return {}

    # 排序坐标
    sorted_coords = sorted(coordinates)
    clusters = {}
    current_cluster = 0
    clusters[current_cluster] = [sorted_coords[0], sorted_coords[0]]  # [min, max]

    for coord in sorted_coords[1:]:
        # 如果当前坐标与上一聚类的最大差值小于阈值，则归为同一聚类
        if coord - clusters[current_cluster][1] <= threshold:
            clusters[current_cluster][1] = coord
        else:
            current_cluster += 1
            clusters[current_cluster] = [coord, coord]

    return clusters


def print_table(table_data):
    """格式化打印表格"""
    if not table_data:
        print("没有表格数据")
        return

    # 计算每列的最大宽度
    col_widths = []
    for col_idx in range(max(len(row) for row in table_data)):
        max_width = max(len(str(row[col_idx])) if col_idx < len(row) else 0 for row in table_data)
        col_widths.append(max_width)

    # 打印表格
    for row in table_data:
        row_str = "| "
        for col_idx, cell in enumerate(row):
            # 按列宽对齐
            row_str += f"{cell.ljust(col_widths[col_idx])} | "
        print(row_str)
        # 打印分隔线
        if table_data.index(row) == 0:
            print("+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+")


if __name__ == "__main__":
    # 替换为你的表格图片路径
    image_path = "/Users/tyrtao/模型/f2bd9d30751028873f5267fdd47e263.jpg"

    # 识别表格
    table_data = recognize_table_with_easyocr(image_path)

    if table_data:
        print("表格识别结果：")
        print_table(table_data)
    else:
        print("表格识别失败")
