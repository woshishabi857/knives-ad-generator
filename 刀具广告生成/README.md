# KnifeAd-BatchGen (商业刀具广告图合成渲染工具)

`KnifeAd-BatchGen` 是一款全自动的商业刀具广告图生成工具。你可以将不同类别的**透明背景刀具图 (PNG)** 放入对应的文件夹中，程序会自动将其按比例缩放贴至预设的**高清背景模板**，并提取蒙版，最终利用 **Gemini 3 (Imagen 3)** 模型进行高质量的光影与质感重绘，批量生成极具商业质感的顶级广告成片。

## ⚙️ 1. 环境准备与配置

### 安装依赖
确保您已安装 Python，并在终端进入本目录，然后执行：
```bash
pip install -r requirements.txt
```

### 配置 API Key
1. 在项目根目录下打开 `.env` 文件。
2. 将 `GEMINI_API_KEY="YOUR_API_KEY_HERE"` 替换为您申请到的真实 Google Gemini API Key。

## 📁 2. 准备底图与素材

### 2.1 放置背景模板
你需要首先在 `assets/backgrounds/` 目录下放置各种场景的高清背景图：
- `bg_meat.jpg` (用于切肉刀场景，如木纹、生肉等)
- `bg_veg.jpg` (用于蔬菜刀场景)
- `bg_fruit.jpg` (用于水果刀场景)
- `bg_box.jpg` (用于包装盒场景)
- `bg_combo.jpg` (用于组合套装场景)

*(注意文件名请与 `config.py` 中的配置路径保持一致)*

### 2.2 放置待处理刀具
在 `input_knives/` 下已为您建立好分类目录（例如 `meat/`, `veg/`, `fruit/` 等）。
- 请将被抠除背景、拥有 **Alpha 透明通道** 的刀具图片（必须是 **`.png`**）放入对应的文件夹。例如：切肉刀的图就放在 `input_knives/meat/` 下。

## 🚀 3. 开始执行生成

在终端里回到项目根目录，直接运行以下命令：
```bash
python main.py
```

执行后，程序将全自动：
1. 扫描 `input_knives` 下的图片并匹配预设场景。
2. 进行本地物理拼接并生成供 AI 锁定的 `mask.png`。
3. 自动调用 API 执行生图重绘（自带容错与超时重试）。
4. 在 `output/` 内对应的分类文件夹下输出前缀为 `rendered_` 的最终高清广告成品。

## 📝 4. 进阶参数微调

如果你想更改**背景图路径**、调整每个场景特定保留的**提示词 (Prompt)**，或者改变刀具的**贴图比例缩放 (scale_ratio)**，你可以打开根目录下的 `config.py` 文件，修改 `SCENES` 字典即可。所有配置均是即时生效的。
