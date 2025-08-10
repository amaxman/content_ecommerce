import pytesseract
from PIL import Image


def recognize_text(image_path):
    """
    识别图片中的文字
    :param image_path: 图片路径
    :return: 识别出的文字
    """
    try:
        # 打开图片文件
        img = Image.open(image_path)

        # 配置Tesseract OCR路径（如果不是默认路径）
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # 识别图片中的文字
        # lang参数可以指定语言，如'chi_sim'表示简体中文，'eng'表示英文
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')

        return text.strip()
    except Exception as e:
        print(f"识别出错: {e}")
        return None


if __name__ == "__main__":
    # 替换为你的图片路径
    image_path = "/Users/tyrtao/QcHelper/客户账单模型/国测/bb14968b582c2070105476d2ac5048a.jpg"

    # 识别文字
    result = recognize_text(image_path)

    if result:
        print("识别结果：")
        print(result)
    else:
        print("识别失败")
