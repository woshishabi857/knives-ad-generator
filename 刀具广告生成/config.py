# config.py
# 模板与提示词配置中心 (Template & Prompt Configuration)

import os

# 默认基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
INPUT_DIR = os.path.join(BASE_DIR, "input_knives")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 场景配置字典
SCENES = {
    "meat_cleaver": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_meat.jpg"),
        "prompt": "Professional commercial food photography, high-definition, 8k, photorealistic style. A premium kitchen setting featuring an end-grain wood cutting board, a large raw beef steak with rich marbling, fresh rosemary, coarse sea salt crystals, black peppercorns, and whole garlic cloves. The knife from the product photo is placed naturally on the board. IMPORTANT: The knife's exact shape, silhouette, blade proportions, and handle design must be preserved EXACTLY as shown in the product photo — do NOT alter the knife's form in any way. Any logo, text, or engraving on the blade must be reproduced pixel-perfectly. Warm, directional cinematic lighting from the left, casting realistic soft shadows onto the wood grain. Shallow depth of field with softly blurred background.",
    },
    "veg_knife": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_veg.jpg"),
        "prompt": "Professional commercial food photography, 8k. A chef's knife resting on a wooden board surrounded by fresh chopped vegetables and tomatoes. IMPORTANT: The knife's exact shape and silhouette must be preserved EXACTLY as in the product photo — do NOT alter the knife's form. Any logo or engraving on the blade must be reproduced pixel-perfectly. Bright natural kitchen lighting, realistic shadows.",
        "scale_ratio": 0.60
    },
    "fruit_knife": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_fruit.jpg"),
        "prompt": "Bright, fresh commercial photography. A paring knife on a light wood board next to sliced peaches and berries. IMPORTANT: The knife's exact shape and silhouette must be preserved EXACTLY as in the product photo — do NOT alter the knife's form. Any logo or engraving on the blade must be reproduced pixel-perfectly. Soft morning light, hyper-realistic integration.",
        "scale_ratio": 0.45  # 水果刀相对小一点
    },
    "packaging": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_box.jpg"),
        "prompt": "Luxury product photography, 8k resolution. An exquisite knife placed elegantly beside or inside its premium presentation box lined with velvet. IMPORTANT: The knife's exact shape and silhouette must be preserved EXACTLY as in the product photo — do NOT alter the knife's form. Any logo, text, or brand mark on the blade must be reproduced pixel-perfectly. Soft, diffused studio lighting highlighting the metallic gleam and the texture of the packaging.",
        "scale_ratio": 0.50
    },
    "combo_set": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_combo.jpg"),
        "prompt": "High-end culinary magazine cover style, 8k, photorealistic. A stunning layout of a chef's knife set on a pristine marble countertop with subtle professional kitchen elements in the blurred background. IMPORTANT: Each knife's exact shape and silhouette must be preserved EXACTLY as in the product photo — do NOT alter any knife's form. All logos, text, and engravings on blades must be reproduced pixel-perfectly. Dramatic directional lighting casting crisp shadows, perfect composition.",
        "scale_ratio": 0.65
    },
    "forest": {
        "bg_path": os.path.join(ASSETS_DIR, "backgrounds", "bg_forest.png"),
        "prompt": "Cinematic outdoor adventure photography, 8k, ultra-photorealistic. A rugged bushcraft knife resting on a mossy log in a lush forest setting with dappled sunlight filtering through the canopy. IMPORTANT: The knife's exact shape, silhouette, blade proportions, and handle design must be preserved EXACTLY as shown in the product photo — do NOT alter the knife's form in any way. Any logo, text, or engraving on the blade must be reproduced pixel-perfectly. Rich earthy tones, natural golden-hour lighting casting warm, realistic shadows on the bark and moss. Seamless integration with the woodland environment.",
        "scale_ratio": 0.55
    }
}
