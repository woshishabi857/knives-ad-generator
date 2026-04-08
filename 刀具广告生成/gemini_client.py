import os
import io
import time
import httpx
import base64
from PIL import Image
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


def _image_to_base64_data_uri(img):
    buffer = io.BytesIO()
    # 转为RGB避免透明通道在某些不受支持的模型上报错
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    img.save(buffer, format="JPEG", quality=95)
    b64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64

def _call_ark_image_generation(api_key, endpoint_id, prompt, images, max_retries=3):
    api_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": endpoint_id,
        "prompt": prompt,
        "image": images, # Ark多图输入/单图生图通用参数
        "watermark": False # 官方设置：设为 False 即可关闭左下角的“AI生成”水印
    }
    
    for attempt in range(max_retries):
        try:
            print(f">>> [Ark API] 尝试发送求 (尝试 {attempt + 1}/{max_retries})...")
            response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                raise ValueError(f"Ark API 错误: {response.status_code} - {response.text}")
                
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                image_url = data["data"][0].get("url")
                if image_url:
                    print(f">>> [Ark API] 生成成功，正在下载图片...")
                    img_resp = httpx.get(image_url, timeout=30)
                    if img_resp.status_code == 200:
                        return img_resp.content
                    else:
                        raise ValueError(f"下载生成的图片失败: {img_resp.status_code}")
                # Some API configs return b64_json
                image_b64 = data["data"][0].get("b64_json")
                if image_b64:
                    return base64.b64decode(image_b64)
            raise ValueError(f"返回结果中没有图像数据: {data}")
            
        except Exception as e:
            print(f">>> [Ark API] 请求失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                raise e
    return None

def generate_ad_image(bg_path, knife_path, prompt, output_path, composition="", max_retries=3, cancel_event=None):
    """
    基于火山方舟 Ark 平台，使用 Seedream/Doubao 大模型进行图生图。
    """
    api_key = os.environ.get("ARK_API_KEY")
    endpoint_id = os.environ.get("ARK_ENDPOINT_ID")
    
    if not api_key or not endpoint_id:
        print(">>> 错误: 请完善 .env 文件中的 ARK_API_KEY 和 ARK_ENDPOINT_ID 配置。")
        return False

    try:
        bg_img = Image.open(bg_path).convert("RGB")
        knife_img = Image.open(knife_path).convert("RGBA")

        # 限制图片尺寸
        max_side = 1024
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

    comp_prefix = f"The product knife is made of {composition}. " if composition else ""
    full_prompt = (
        f"{prompt}\n\n"
        f"PRODUCT DESCRIPTION: {comp_prefix}The material and texture of the knife shown in image 2 should be realistically rendered and integrated into the scene.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Image 1 is the BACKGROUND SCENE.\n"
        "- Image 2 is the PRODUCT KNIFE photograph.\n\n"
        "Generate an ultra-photorealistic advertisement image by placing the knife into the background scene.\n\n"
    )

    bg_b64 = _image_to_base64_data_uri(bg_img)
    knife_b64 = _image_to_base64_data_uri(knife_img)
    
    try:
        if cancel_event and cancel_event.is_set():
            return False
        
        image_bytes = _call_ark_image_generation(api_key, endpoint_id, full_prompt, [bg_b64, knife_b64], max_retries=max_retries)
        if image_bytes:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f">>> [成功] API 渲染完毕，最终文件已存至 -> {output_path}")
            return True
    except Exception as e:
        print(f">>> [API 异常] 最终失败: {e}")
        
    return False

def generate_ad_image_bytes(bg_img, knife_img, prompt, composition="", max_retries=3, cancel_event=None):
    """
    Web API 专用版本
    """
    api_key = os.environ.get("ARK_API_KEY")
    endpoint_id = os.environ.get("ARK_ENDPOINT_ID")
    if not api_key or not endpoint_id:
        return False, "请配置 ARK_API_KEY 和 ARK_ENDPOINT_ID (前往火山方舟控制台获取)"

    max_side = 1024
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
    )

    bg_b64 = _image_to_base64_data_uri(bg_img)
    knife_b64 = _image_to_base64_data_uri(knife_img)
    
    if cancel_event and cancel_event.is_set():
        return False, "任务已被取消"

    try:
        image_bytes = _call_ark_image_generation(api_key, endpoint_id, full_prompt, [bg_b64, knife_b64], max_retries=max_retries)
        if image_bytes:
            return True, image_bytes
        else:
            return False, "返回空结果"
    except Exception as e:
        return False, f"Ark API 异常: {e}"

def generate_ad_image_bytes_combo(bg_img, knife_imgs, prompt, compositions=[], max_retries=3, cancel_event=None):
    """
    组合模式 Web API 版本
    """
    api_key = os.environ.get("ARK_API_KEY")
    endpoint_id = os.environ.get("ARK_ENDPOINT_ID")
    if not api_key or not endpoint_id:
        return False, "请配置 ARK_API_KEY 和 ARK_ENDPOINT_ID (前往火山方舟控制台获取)"

    max_side = 1024
    w, h = bg_img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        bg_img = bg_img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        
    resized_knife_imgs = []
    for knife_img in knife_imgs:
        w, h = knife_img.size
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            resized_knife_imgs.append(knife_img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS))
        else:
            resized_knife_imgs.append(knife_img)

    knife_descriptions = []
    for i, composition in enumerate(compositions):
        if composition:
            knife_descriptions.append(f"Knife {i+1} is made of {composition}.")
        else:
            knife_descriptions.append(f"Knife {i+1}.")
    comp_prefix = " ".join(knife_descriptions) + " " if knife_descriptions else ""

    instructions = "CRITICAL INSTRUCTIONS:\n- Image 1 is the BACKGROUND SCENE.\n"
    for i in range(len(resized_knife_imgs)):
        instructions += f"- Image {i+2} is a PRODUCT KNIFE referenced photograph.\n"
    
    full_prompt = (
        f"{prompt}\n\n"
        f"PRODUCT DESCRIPTION: {comp_prefix}All knives should be realistically rendered and integrated into the scene.\n\n"
        f"{instructions}\n"
        f"Generate an ultra-photorealistic advertisement image by placing all knives into the background scene."
    )

    all_images = [bg_img] + resized_knife_imgs
    b64_list = [_image_to_base64_data_uri(img) for img in all_images]
    
    if cancel_event and cancel_event.is_set():
        return False, "任务已被取消"

    try:
        image_bytes = _call_ark_image_generation(api_key, endpoint_id, full_prompt, b64_list, max_retries=max_retries)
        if image_bytes:
            return True, image_bytes
        else:
            return False, "返回空结果"
    except Exception as e:
        return False, f"Ark API 异常: {e}"
