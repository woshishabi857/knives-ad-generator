import os
import glob
from config import SCENES, INPUT_DIR, OUTPUT_DIR
from gemini_client import generate_ad_image

def main():
    print("=== KnifeAd-BatchGen 批量生成启动 ===")
    
    if not os.path.exists(INPUT_DIR):
        print(f"Error: 找不到输入目录 {INPUT_DIR}")
        return
        
    categories = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
    if not categories:
        print(f"未在 {INPUT_DIR} 下找到任何目录。请依照分类建立子文件夹并放入刀具图片。")
        return

    for category in categories:
        # 通过匹配 category 名称与 SCENE keys 对应
        scene_key = None
        for key in SCENES.keys():
            if category in key or key in category:
                scene_key = key
                break
                
        if not scene_key:
            print(f"警告: 输入目录 '{category}' 无法匹配到配置中的场景类型，跳过...")
            continue
            
        scene_config = SCENES[scene_key]
        bg_path = scene_config['bg_path']
        prompt = scene_config['prompt']
        
        if not os.path.exists(bg_path):
            print(f"警告: 场景 '{scene_key}' 预设背景图不存在: {bg_path}")
            print(">>> 请先将对应的背景图放置再执行。跳过...")
            continue

        category_in_dir = os.path.join(INPUT_DIR, category)
        category_out_dir = os.path.join(OUTPUT_DIR, category)
        
        image_files = glob.glob(os.path.join(category_in_dir, "*.png")) + glob.glob(os.path.join(category_in_dir, "*.jpg"))
        if not image_files:
            continue
            
        print(f"\n---> 开始处理场景: {scene_key} (匹配目录: {category}, 共 {len(image_files)} 张图)")
        for knife_file in image_files:
            filename = os.path.basename(knife_file)
            print(f"\n[处理对象]: {filename}")
            
            # 直接调用 API，发送原始背景图 + 刀具图
            final_output_path = os.path.join(category_out_dir, f"rendered_{filename}")
            if os.path.exists(final_output_path):
                print(f"  - 存在同名成品，直接跳过: {final_output_path}")
                continue
                
            print("  - 发起 Gemini 云端融合渲染...")
            success = generate_ad_image(
                bg_path=bg_path,
                knife_path=knife_file,
                prompt=prompt,
                output_path=final_output_path
            )
            
            if success:
                print(f"  - [完成] 成片已收录至: {final_output_path}")
            else:
                print(f"  - [报错] 最终渲染异常。")

    print("\n=== 批量处理结束 ===")

if __name__ == "__main__":
    main()
