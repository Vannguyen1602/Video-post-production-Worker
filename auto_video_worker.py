import requests
import json
import time
import os
import re
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycxvo8PlYnz2MeKTltiPDNBr8uihoxy583YGECG4F5p0BLKQRQ7Q1PcXdEp8qSeIPjvfSA/exec"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERVAL_SECONDS = 60 

# --- AI CLIENT ---
client = genai.Client(api_key=GEMINI_API_KEY)

def upload_to_catbox(file_path):
    """Upload file lên Catbox và trả về link trực tiếp."""
    if not os.path.exists(file_path): return None
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, files=files, data=data, timeout=60)
        return response.text.strip() if response.status_code == 200 else None
    except: return None

def generate_pillow_thumbnail(title_text, output_path="thumb.png"):
    """
    Logic 'Vẽ tay' Giai đoạn 5: Tạo ảnh thumbnail với Guider & Student nhất quán.
    - Guider: Đầu chữ nhật, vest đen, huy hiệu đỏ.
    - Student: Đầu tròn, tóc dựng, tất sọc.
    """
    # Tạo nền rực rỡ (Vibrant background)
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color=(255, 223, 0)) # Nền vàng rực
    draw = ImageDraw.Draw(img)
    
    # Vẽ Guider (Đầu chữ nhật, vest đen)
    draw.rectangle([100, 200, 350, 600], fill=(30, 30, 30)) # Thân vest đen
    draw.rectangle([150, 100, 300, 250], fill=(255, 200, 150)) # Đầu chữ nhật
    draw.ellipse([180, 150, 200, 170], fill=(0, 0, 0)) # Mắt
    draw.ellipse([250, 150, 270, 170], fill=(0, 0, 0)) # Mắt
    draw.polygon([(225, 170), (215, 200), (235, 200)], fill=(255, 100, 100)) # Mũi nhọn
    draw.rectangle([120, 300, 150, 330], fill=(255, 0, 0)) # Huy hiệu đỏ
    
    # Vẽ Student (Đầu tròn, tất sọc)
    draw.ellipse([900, 350, 1150, 600], fill=(30, 144, 255)) # Thân xanh
    draw.ellipse([950, 200, 1100, 350], fill=(255, 220, 180)) # Đầu tròn
    draw.line([(970, 200), (980, 170), (1000, 200)], fill=(0, 0, 0), width=5) # Tóc dựng
    draw.line([(1020, 200), (1030, 160), (1050, 200)], fill=(0, 0, 0), width=5) # Tóc dựng
    # Chân tất sọc
    draw.rectangle([950, 600, 980, 700], fill=(255, 255, 255))
    for i in range(600, 700, 20): draw.line([(950, i), (980, i)], fill=(255, 0, 0), width=5)
    
    # Thêm text tiêu đề (Title Text)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Verdana Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    # Vẽ nền cho chữ (Box)
    draw.rectangle([350, 50, 930, 150], fill=(255, 0, 0))
    draw.text((370, 60), title_text[:25], fill=(255, 255, 255), font=font)
    
    img.save(output_path)
    return output_path

def get_tasks():
    try:
        response = requests.get(WEBHOOK_URL, params={"action": "get_tasks"}, timeout=30)
        return response.json() if response.status_code == 200 else []
    except: return []

def update_task(task_id, caption, hashtags, thumb_url):
    payload = {
        "action": "update_task", "id": task_id, "caption": caption, 
        "hashtags": hashtags, "thumbnail": thumb_url, "status": "Done"
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=30)
        return True
    except: return False

def ai_process(topic, state):
    prompt = f"Create TikTok content for DMV {state}: {topic}. Output XML: <CAPTION>, <HASHTAGS>, <TITLE>"
    try:
        res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        text = res.text
        cap = re.search(r'<CAPTION>(.*?)</CAPTION>', text, re.DOTALL).group(1).strip()
        tags = re.search(r'<HASHTAGS>(.*?)</HASHTAGS>', text, re.DOTALL).group(1).strip()
        title = re.search(r'<TITLE>(.*?)</TITLE>', text, re.DOTALL).group(1).strip()
        return cap, tags, title
    except: return None, None, None

def run_worker():
    print("🤖 Video Factory Worker v4.0 (Local Image Gen + Catbox)...")
    while True:
        tasks = get_tasks()
        for task in tasks:
            t_id = task.get('id')
            print(f"Processing Task {t_id}...")
            cap, tags, title = ai_process(task.get('topic'), task.get('state'))
            if cap and tags:
                # Giai đoạn 5: Tự vẽ ảnh thay vì gọi API
                local_img = generate_pillow_thumbnail(title)
                catbox_link = upload_to_catbox(local_img)
                if update_task(t_id, cap, tags, catbox_link):
                    print(f"✅ Task {t_id} DONE with Pillow Image!")
        time.sleep(60)

if __name__ == "__main__":
    run_worker()
