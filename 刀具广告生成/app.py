"""
KnifeAd Web — Flask 后端 (批量模式)
启动: python app.py
访问: http://localhost:8080
"""

import os
import io
import base64
import uuid
import json
import threading
from flask import Flask, render_template, request, jsonify
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from gemini_client import generate_ad_image_bytes, generate_ad_image_bytes_combo
from config import SCENES, ASSETS_DIR

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max (batch uploads)

# 任务状态存储 { task_id: { status, total, completed, results: [{...}], errors: [...] } }
tasks = {}
tasks_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """返回预设场景列表"""
    presets = []
    for key, scene in SCENES.items():
        bg_path = scene["bg_path"]
        thumb_b64 = ""
        if os.path.exists(bg_path):
            try:
                img = Image.open(bg_path).convert("RGB")
                img.thumbnail((300, 200))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                thumb_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception:
                pass
        presets.append({
            "key": key,
            "name": key.replace("_", " ").title(),
            "prompt": scene["prompt"],
            "thumbnail": thumb_b64,
            "bg_path": bg_path,
        })
    return jsonify(presets)


@app.route("/api/batch_generate", methods=["POST"])
def batch_generate():
    """
    批量生成接口。
    接收:
    - knife_images: 多个刀具图文件
    - scenes: JSON 数组, 每项 { bg_type: 'preset'|'custom', preset_key?, bg_index?, prompt }
    - bg_images: 自定义背景图文件 (可选)
    """
    knife_files = request.files.getlist("knife_images")
    scenes_json = request.form.get("scenes", "[]")
    bg_files = request.files.getlist("bg_images")

    if not knife_files:
        return jsonify({"success": False, "error": "请至少上传一张刀具图"}), 400

    try:
        scenes = json.loads(scenes_json)
    except Exception:
        return jsonify({"success": False, "error": "场景配置解析失败"}), 400

    if not scenes:
        return jsonify({"success": False, "error": "请至少添加一个场景任务"}), 400

    # 预读所有刀具图
    knife_images = []
    knife_names = []
    for f in knife_files:
        try:
            img = Image.open(f.stream).convert("RGBA")
            knife_images.append(img)
            knife_names.append(f.filename or f"knife_{len(knife_images)}")
        except Exception as e:
            return jsonify({"success": False, "error": f"刀具图读取失败: {e}"}), 400

    # 预读所有背景图
    bg_images_custom = {}
    for i, f in enumerate(bg_files):
        try:
            img = Image.open(f.stream).convert("RGB")
            bg_images_custom[i] = img
        except Exception as e:
            return jsonify({"success": False, "error": f"第 {i+1} 张背景图读取失败: {e}"}), 400

    knives_metadata_json = request.form.get("knives_metadata", "[]")
    try:
        knives_metadata = json.loads(knives_metadata_json)
    except Exception:
        knives_metadata = []

    # 构建任务列表: 每个刀具 × 每个场景 (根据分类过滤)
    task_list = []
    for scene in scenes:
        bg_type = scene.get("bg_type", "preset")
        prompt = scene.get("prompt", "").strip()
        scene_name = scene.get("name", "unknown")
        selected_cats = scene.get("selected_categories", [])
        combo_mode = scene.get("combo_mode", False)

        if not prompt:
            continue

        bg_img = None
        if bg_type == "preset":
            preset_key = scene.get("preset_key", "")
            if preset_key in SCENES:
                bg_path = SCENES[preset_key]["bg_path"]
                if os.path.exists(bg_path):
                    bg_img = Image.open(bg_path).convert("RGB")
        elif bg_type == "custom":
            bg_index = scene.get("bg_index", -1)
            if bg_index in bg_images_custom:
                bg_img = bg_images_custom[bg_index]

        if bg_img is None:
            continue

        if combo_mode:
            # 组合模式：将所有匹配的刀具作为一个列表传递
            matched_knives = []
            matched_knife_names = []
            matched_compositions = []
            for idx, knife_img in enumerate(knife_images):
                # 获取配置
                knife_cat = "general"
                knife_comp = ""
                if idx < len(knives_metadata):
                    knife_cat = knives_metadata[idx].get("category", "general")
                    knife_comp = knives_metadata[idx].get("composition", "")

                # 分类过滤器
                if selected_cats and knife_cat not in selected_cats:
                    continue

                matched_knives.append(knife_img)
                matched_knife_names.append(knife_names[idx])
                matched_compositions.append(knife_comp)

            if matched_knives:
                task_list.append({
                    "knife_imgs": matched_knives,
                    "knife_names": matched_knife_names,
                    "bg_img": bg_img,
                    "prompt": prompt,
                    "compositions": matched_compositions,
                    "scene_name": scene_name,
                    "combo_mode": True
                })
        else:
            # 单刀模式：每个刀具算一个任务
            for idx, knife_img in enumerate(knife_images):
                # 获取配置
                knife_cat = "general"
                knife_comp = ""
                if idx < len(knives_metadata):
                    knife_cat = knives_metadata[idx].get("category", "general")
                    knife_comp = knives_metadata[idx].get("composition", "")

                # 分类过滤器
                if selected_cats and knife_cat not in selected_cats:
                    continue

                task_list.append({
                    "knife_img": knife_img,
                    "knife_name": knife_names[idx],
                    "bg_img": bg_img,
                    "prompt": prompt,
                    "composition": knife_comp,
                    "scene_name": scene_name,
                    "combo_mode": False
                })

    if not task_list:
        return jsonify({"success": False, "error": "没有有效的生成任务"}), 400

    # 创建批量任务
    task_id = str(uuid.uuid4())[:8]
    # 创建取消事件
    cancel_event = threading.Event()
    with tasks_lock:
        tasks[task_id] = {
            "status": "running",
            "total": len(task_list),
            "completed": 0,
            "results": [],
            "errors": [],
            "cancel_event": cancel_event
        }

    # 后台线程处理
    def process_batch():
        for item in task_list:
            # 检查是否取消
            with tasks_lock:
                current_task = tasks.get(task_id)
                if not current_task:
                    break
                cancel_event = current_task.get("cancel_event")
                if cancel_event and cancel_event.is_set():
                    break
            
            if item.get("combo_mode", False):
                # 组合模式
                label = f"{item['scene_name']}_combo"
                try:
                    success, result = generate_ad_image_bytes_combo(
                        item["bg_img"], item["knife_imgs"], item["prompt"], item.get("compositions", []),
                        cancel_event=cancel_event
                    )
                    with tasks_lock:
                        tasks[task_id]["completed"] += 1
                        if success:
                            b64 = base64.b64encode(result).decode("utf-8")
                            tasks[task_id]["results"].append({
                                "label": label,
                                "image": b64,
                                "composition": item.get("composition", ""),
                                "compositions": item.get("compositions", [])
                            })
                        else:
                            tasks[task_id]["errors"].append(f"{label}: {result}")
                except Exception as e:
                    with tasks_lock:
                        tasks[task_id]["completed"] += 1
                        tasks[task_id]["errors"].append(f"{label}: {str(e)}")
            else:
                # 单刀模式
                label = f"{item['scene_name']}_{item['knife_name']}"
                try:
                    success, result = generate_ad_image_bytes(
                        item["bg_img"], item["knife_img"], item["prompt"], item.get("composition", ""),
                        cancel_event=cancel_event
                    )
                    with tasks_lock:
                        tasks[task_id]["completed"] += 1
                        if success:
                            b64 = base64.b64encode(result).decode("utf-8")
                            tasks[task_id]["results"].append({
                                "label": label,
                                "image": b64,
                                "composition": item.get("composition", ""),
                                "compositions": item.get("compositions", [])
                            })
                        else:
                            tasks[task_id]["errors"].append(f"{label}: {result}")
                except Exception as e:
                    with tasks_lock:
                        tasks[task_id]["completed"] += 1
                        tasks[task_id]["errors"].append(f"{label}: {str(e)}")

        with tasks_lock:
            tasks[task_id]["status"] = "done"

    thread = threading.Thread(target=process_batch, daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "task_id": task_id,
        "total": len(task_list),
    })


@app.route("/api/task_status/<task_id>", methods=["GET"])
def task_status(task_id):
    """查询批量任务进度"""
    with tasks_lock:
        task = tasks.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404

    return jsonify({
        "success": True,
        "status": task["status"],
        "total": task["total"],
        "completed": task["completed"],
        "results": task["results"],
        "errors": task["errors"],
    })


@app.route("/api/task_cancel/<task_id>", methods=["POST"])
def task_cancel(task_id):
    """取消批量任务"""
    with tasks_lock:
        task = tasks.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404
    
    if task["status"] == "done":
        return jsonify({"success": False, "error": "任务已完成"}), 400
    
    # 设置取消事件
    cancel_event = task.get("cancel_event")
    if cancel_event:
        cancel_event.set()
        task["status"] = "cancelled"
    
    return jsonify({"success": True, "message": "任务已取消"})


if __name__ == "__main__":
    app.run(host="localhost", port=3000, debug=True)
