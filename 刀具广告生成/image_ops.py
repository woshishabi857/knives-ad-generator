import os
from PIL import Image

def process_composite_and_mask(bg_path, knife_path, output_dir, scale_ratio=0.60):
    """
    处理图像合成并生成黑白蒙版。
    """
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 打开图片
        bg_img = Image.open(bg_path).convert("RGB")
        knife_img = Image.open(knife_path).convert("RGBA")
    except Exception as e:
        print(f"Error loading images: {e}")
        return None, None

    bg_w, bg_h = bg_img.size
    
    # 缩放刀具图片
    target_knife_w = int(bg_w * scale_ratio)
    knife_w, knife_h = knife_img.size
    ratio = target_knife_w / knife_w
    target_knife_h = int(knife_h * ratio)
    
    knife_img = knife_img.resize((target_knife_w, target_knife_h), Image.Resampling.LANCZOS)
    
    # 计算居中坐标
    pos_x = (bg_w - target_knife_w) // 2
    pos_y = (bg_h - target_knife_h) // 2
    
    # 物理拼贴 composite_temp.jpg
    composite_img = bg_img.copy()
    # paste 的第三个参数是 mask，使用刀具自带的 Alpha 通道进行透明混贴
    composite_img.paste(knife_img, (pos_x, pos_y), knife_img)
    
    composite_path = os.path.join(output_dir, "composite_temp.jpg")
    composite_img.save(composite_path, quality=95)
    
    # 生成高精度黑白蒙版 mask.png (白色代表前景，黑色代表背景)
    mask_img = Image.new("L", bg_img.size, color=0)
    knife_alpha = knife_img.split()[3]
    mask_img.paste(knife_alpha, (pos_x, pos_y))
    
    # 二值化，大于 10 的 Alpha 都算前景 (纯白)，消除半透明边缘导致的干扰
    # Gemini Inpainting mask 纯白色部分是可保留的，还是纯黑部分可保留？
    # 注意：在许多 Inpainting 模型中，Mask 中的白色代表【需重绘/修改区域】，黑色代表【保持原样区域】
    # 但是，针对此“背景替换 / 指定保留物体”需求，我们需要结合 Prompt。
    # 往往 Inpainting mask 是：选中的区域被改变。
    # 我们要融合刀锋还是保留刀锋？
    mask_img = mask_img.point(lambda p: 255 if p > 10 else 0)
    
    mask_path = os.path.join(output_dir, "mask.png")
    mask_img.save(mask_path)
    
    return composite_path, mask_path
