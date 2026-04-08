import os
import io
import time
import httpx
import base64
import hashlib
import hmac
import json
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
ak = os.environ.get("VOLCENGINE_AK")
sk = os.environ.get("VOLCENGINE_SK")

def generate_volcengine_signature(ak, sk, service, region, timestamp, action, version, payload_bytes=b""):
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    canonical_headers = f"content-type:application/json\nhost:open.volcengineapi.com\nx-content-sha256:{payload_hash}\nx-date:{timestamp}\n"
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = f"POST\n/\nAction={action}&Version={version}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    date_int = timestamp[:8]
    credential_scope = f"{date_int}/{region}/{service}/request"
    canonical_request_hash = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    string_to_sign = f"HMAC-SHA256\n{timestamp}\n{credential_scope}\n{canonical_request_hash}"
    kDate = hmac.new(sk.encode('utf-8'), date_int.encode('utf-8'), hashlib.sha256).digest()
    kRegion = hmac.new(kDate, region.encode('utf-8'), hashlib.sha256).digest()
    kService = hmac.new(kRegion, service.encode('utf-8'), hashlib.sha256).digest()
    kSigning = hmac.new(kService, b'request', hashlib.sha256).digest()
    signature = hmac.new(kSigning, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}", payload_hash

def test_api():
    payload = {
        "Service": "ImageGeneration",
        "Method": "ImageGeneration",
        "Parameters": {
            "prompt": "ABC", "size": "1024x1024", "images": [{"data": "AAA", "type": "png"}]
        }
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    # Let's try Action=ImageGeneration or CVSubmitTask
    actions = ["ImageGeneration", "CVSubmitTask"]
    for act in actions:
        sig, phash = generate_volcengine_signature(ak, sk, "cv", "cn-north-1", timestamp, act, "2022-08-31", payload_bytes)
        headers = {
            "Content-Type": "application/json",
            "X-Date": timestamp,
            "X-Content-Sha256": phash,
            "Authorization": sig
        }
        api_url = f"https://open.volcengineapi.com/?Action={act}&Version=2022-08-31"
        response = httpx.post(api_url, headers=headers, content=payload_bytes, timeout=10)
        print(f"[{act}] {response.status_code} - {response.text}")

test_api()
