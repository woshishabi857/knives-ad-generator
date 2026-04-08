import os
import io
import time
import httpx
import base64
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

def test_api():
    api_key = os.environ.get("ARK_API_KEY")
    endpoint_id = os.environ.get("ARK_ENDPOINT_ID")
    
    img = Image.new('RGB', (512, 512), color = 'red')
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    b64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    api_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": endpoint_id,
        "prompt": "ABC",
        "image": [b64]
    }
    
    response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
    print(f"[{endpoint_id}] {response.status_code} - {response.text}")

test_api()
