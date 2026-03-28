import os
import io
import time
import httpx
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


def get_closest_aspect_ratio(w, h):
    """
    根据给定的宽高计算最接近的 Google GenAI 支持的 aspect_ratio 字符串。
    支持: "1:1", "4:3", "3:4", "16:9", "9:16"
    """
    if h == 0:
        return "1:1"
    ratio = w / h
    # 标准比例定义
    targets = [
        (1.0, "1:1"),
        (1.333, "4:3"),
        (0.75, "3:4"),
        (1.777, "16:9"),
        (0.5625, "9:16")
    ]
    best_match = targets[0][1]
    min_diff = float('inf')
    for val, label in targets:
        diff = abs(ratio - val)
        if diff < min_diff:
            min_diff = diff
            best_match = label
    return best_match


def generate_ad_image(bg_path, knife_path, prompt, output_path, composition="", max_retries=3):
    """
    调用 Google GenAI 接口，直接发送原始背景图 + 刀具图进行 AI 融合生成广告图。
    不再预先合成/蒙版，让 Gemini 自主完成高质量融合。
    支持通过 HTTP_PROXY / HTTPS_PROXY 环境变量设置代理。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print(">>> 错误: 请完善 .env 文件中的 GEMINI_API_KEY 配置。")
        return False

    # ---------- 代理支持 ----------
    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy") or os.environ.get("http_proxy")

    try:
        if proxy_url:
            print(f">>> 检测到代理配置: {proxy_url}")
            http_client = httpx.Client(proxy=proxy_url, timeout=120)
            client = genai.Client(api_key=api_key, http_options={"client": http_client})
        else:
            client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f">>> 初始化 Client 失败: {e}")
        return False

    # ---------- 读取图片 ----------
    try:
        bg_img = Image.open(bg_path).convert("RGB")
        knife_img = Image.open(knife_path).convert("RGBA")

        # 限制图片尺寸，避免请求体过大导致超时
        max_side = 1536
        for label, img in [("bg", bg_img), ("knife", knife_img)]:
            w, h = img.size
            if max(w, h) > max_side:
                ratio = max_side / max(w, h)
                new_size = (int(w * ratio), int(h * ratio))
                if label == "bg":
                    bg_img = bg_img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    knife_img = knife_img.resize(new_size, Image.Resampling.LANCZOS)

    except Exception as e:
        print(f">>> 读取源图失败: {e}")
        return False

    # ---------- 构建 Prompt ----------
    comp_prefix = f"The product knife is made of {composition}. " if composition else ""
    full_prompt = (
        f"{prompt}\n\n"
        f"PRODUCT DESCRIPTION: {comp_prefix}The material and texture of the knife shown in image 2 should be realistically rendered and integrated into the scene.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Image 1 is the BACKGROUND SCENE.\n"
        "- Image 2 is the PRODUCT KNIFE photograph.\n\n"
        "Generate an ultra-photorealistic advertisement image by placing the knife into the background scene.\n\n"
        "ABSOLUTE REQUIREMENTS (DO NOT VIOLATE):\n"
        "1. KNIFE SHAPE PRESERVATION: The knife's exact silhouette, blade shape, handle shape, proportions, "
        "and every physical detail must be pixel-perfectly preserved from image 2. "
        "Do NOT alter, reshape, bend, extend, shorten, or modify the knife's form in ANY way. "
        "The knife in the output must be identical in shape to image 2.\n"
        "2. LOGO PRESERVATION: Any text, logo, brand mark, or engraving visible on the knife blade "
        "in image 2 must be reproduced EXACTLY as-is — same text, same font, same position, same size, same orientation. "
        "Do NOT change, remove, or re-interpret the logo.\n"
        "3. Only modify the BACKGROUND and add natural lighting, shadows, and reflections to integrate "
        "the knife into the scene. The knife itself is sacred and untouchable.\n\n"
        "The final result should look like a high-end professional product photograph."
    )

    # 使用当前可用的图像生成模型
    model_id = "gemini-3-pro-image-preview"

    # ---------- API 调用（带重试） ----------
    for attempt in range(max_retries):
        try:
            print(f">>> [API 通信] 开始请求 (第 {attempt + 1}/{max_retries} 次尝试)...")

            # 计算最适合的输出比例
            target_ratio = get_closest_aspect_ratio(bg_img.width, bg_img.height)

            response = client.models.generate_content(
                model=model_id,
                contents=[bg_img, knife_img, full_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=target_ratio
                    )
                )
            )

            # 提取返回的图像
            result_image = None
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_bytes = part.inline_data.data
                        result_image = Image.open(io.BytesIO(image_bytes))
                        break

            if result_image is None:
                text_resp = ""
                try:
                    text_resp = response.text[:200]
                except Exception:
                    pass
                raise ValueError(f"API 未返回图像数据。文字回复: {text_resp}")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result_image.save(output_path, quality=95)

            print(f">>> [成功] API 渲染完毕，最终文件已存至 -> {output_path}")
            return True

        except Exception as e:
            print(f">>> [API 异常] 第 {attempt + 1} 次请求失败，原因: {e}")
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f">>> 等待 {wait} 秒后重试...")
                time.sleep(wait)
            else:
                print(">>> [严重错误] API 重试次数已达上限，跳过该文件的渲染。")
                return False

    return False


def generate_ad_image_bytes(bg_img, knife_img, prompt, composition="", max_retries=3):
    """
    Web API 专用：接收 PIL Image 对象，返回生成图片的字节流。
    成功返回 (True, image_bytes)，失败返回 (False, error_message)。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        return False, "请配置 GEMINI_API_KEY"

    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy") or os.environ.get("http_proxy")

    try:
        if proxy_url:
            http_client = httpx.Client(proxy=proxy_url, timeout=120)
            client = genai.Client(api_key=api_key, http_options={"client": http_client})
        else:
            client = genai.Client(api_key=api_key)
    except Exception as e:
        return False, f"初始化 Client 失败: {e}"

    # 限制图片尺寸
    max_side = 1536
    for label, img in [("bg", bg_img), ("knife", knife_img)]:
        w, h = img.size
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            if label == "bg":
                bg_img = bg_img.resize(new_size, Image.Resampling.LANCZOS)
            else:
                knife_img = knife_img.resize(new_size, Image.Resampling.LANCZOS)

    comp_prefix = f"The product knife is made of {composition}. " if composition else ""
    full_prompt = (
        f"{prompt}\n\n"
        f"PRODUCT DESCRIPTION: {comp_prefix}The material and texture of the knife shown in image 2 should be realistically rendered and integrated into the scene.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Image 1 is the BACKGROUND SCENE.\n"
        "- Image 2 is the PRODUCT KNIFE photograph.\n\n"
        "Generate an ultra-photorealistic advertisement image by placing the knife into the background scene.\n\n"
        "ABSOLUTE REQUIREMENTS (DO NOT VIOLATE):\n"
        "1. KNIFE SHAPE PRESERVATION: The knife's exact silhouette, blade shape, handle shape, proportions, "
        "and every physical detail must be pixel-perfectly preserved from image 2. "
        "Do NOT alter, reshape, bend, extend, shorten, or modify the knife's form in ANY way. "
        "The knife in the output must be identical in shape to image 2.\n"
        "2. LOGO PRESERVATION: Any text, logo, brand mark, or engraving visible on the knife blade "
        "in image 2 must be reproduced EXACTLY as-is — same text, same font, same position, same size, same orientation. "
        "Do NOT change, remove, or re-interpret the logo.\n"
        "3. Only modify the BACKGROUND and add natural lighting, shadows, and reflections to integrate "
        "the knife into the scene. The knife itself is sacred and untouchable.\n\n"
        "The final result should look like a high-end professional product photograph."
    )

    model_id = "gemini-3-pro-image-preview"

    # 计算最适合的输出比例
    target_ratio = get_closest_aspect_ratio(bg_img.width, bg_img.height)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[bg_img, knife_img, full_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=target_ratio
                    )
                )
            )

            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_bytes = part.inline_data.data
                        return True, image_bytes

            text_resp = ""
            try:
                text_resp = response.text[:200]
            except Exception:
                pass
            raise ValueError(f"API 未返回图像数据。文字回复: {text_resp}")

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return False, f"API 调用失败: {e}"

    return False, "未知错误"
