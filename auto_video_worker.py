import requests
import json
import time
import os
import re
from google import genai
from google.genai import types

# --- CONFIGURATION ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzEyiDvDY3bjCi08PRKUu0gU14QEBM4am-Stzb8IlUOKS5LIX4ZzfG3QHTmzoOwwoKVww/exec"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERVAL_SECONDS = 60 

# --- AI CLIENT ---
client = genai.Client(api_key=GEMINI_API_KEY)

def get_tasks():
    try:
        response = requests.get(WEBHOOK_URL, params={"action": "get_tasks"}, timeout=30)
        return response.json() if response.status_code == 200 else []
    except: return []

def update_task(task_row, data):
    payload = {"action": "update_task", "row": task_row, **data}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=30)
        return True
    except: return False

def upload_to_catbox(file_path):
    if not os.path.exists(file_path): return None
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, files=files, data=data, timeout=60)
        return response.text.strip() if response.status_code == 200 else None
    except: return None

def generate_image_ai(prompt, output_path="thumbnail.png"):
    """Thử nghiệm tạo ảnh với các model Imagen khả dụng."""
    # Thử lần lượt các model từ mới đến cũ
    models_to_try = ['imagen-3.0-generate-001', 'imagen-3.0-capability-001', 'imagen-2.0-generate-001']
    
    for model_name in models_to_try:
        try:
            print(f"🎨 Trying to draw with {model_name}...")
            response = client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    output_mime_type='image/png',
                    aspect_ratio='16:9',
                    number_of_images=1
                )
            )
            if response.generated_images:
                with open(output_path, "wb") as f:
                    f.write(response.generated_images[0].image_bytes)
                return output_path
        except Exception as e:
            print(f"⚠️ {model_name} failed: {str(e)[:100]}")
            continue
    return None

def ai_post_production(topic, subtopic, script_content):
    """AI Post-Production v5.8 (Multi-Model Image Gen)."""
    prompt = f"""
    You are a World-Class Social Media Strategist. 
    TASK: Process content for a video based on the Script.
    SCRIPT: {script_content}

    RULES (ALL ENGLISH):
    1. CAPTION (FB/IG/YT): Universal Hook < 125 chars. 3-5 lines body. CTA: Comment keyword.
    2. CAPTION TIKTOK: 1 Hook + 1 CTA. No filler. 
    3. HASHTAGS: 3-5 per platform. 
    4. YOUTUBE TITLE: Golden 60 chars. [SEO Keywords] + (Emotional Hook). Year 2026.
    5. THUMBNAIL (IMAGEN PROMPT): 
       - Style: Professional 2D Animation style, vibrant colors, high contrast.
       - Content: MUST illustrate the core concept of the script.
       - Text: MUST include a very bold, catchy Title text on the image.
       - Characters: Guider (black suit) and Student (round head).

    OUTPUT FORMAT:
    <CAPTION_GENERAL>...</CAPTION_GENERAL>
    <CAPTION_TIKTOK>...</CAPTION_TIKTOK>
    <HASHTAG_TIKTOK>...</HASHTAG_TIKTOK>
    <HASHTAG_FACEBOOK>...</HASHTAG_FACEBOOK>
    <HASHTAG_YOUTUBE>...</HASHTAG_YOUTUBE>
    <HASHTAG_INSTAGRAM>...</HASHTAG_INSTAGRAM>
    <TITLE_YOUTUBE>...</TITLE_YOUTUBE>
    <THUMBNAIL_PROMPT>...</THUMBNAIL_PROMPT>
    """

    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        text = response.text
        def extract(tag):
            match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
            return match.group(1).strip() if match else ""

        results = {
            "caption": extract("CAPTION_GENERAL"),
            "caption_tiktok": extract("CAPTION_TIKTOK"),
            "hashtag_tiktok": extract("HASHTAG_TIKTOK"),
            "hashtag_facebook": extract("HASHTAG_FACEBOOK"),
            "hashtag_youtube": extract("HASHTAG_YOUTUBE"),
            "hashtag_instagram": extract("HASHTAG_INSTAGRAM"),
            "title youtube": extract("TITLE_YOUTUBE")
        }
        
        # THỰC HIỆN VẼ ẢNH
        img_prompt = extract("THUMBNAIL_PROMPT")
        if img_prompt:
            img_file = generate_image_ai(img_prompt)
            if img_file:
                url = upload_to_catbox(img_file)
                if url:
                    results["thumbnail"] = url
                    print(f"🔗 Image Uploaded: {url}")
                else: results["thumbnail"] = "Upload Failed"
            else: results["thumbnail"] = "Drawing Failed"
        
        return results
    except: return None

def run_worker():
    print("🤖 Video Factory Worker v5.8 (Gemini Image Gen) started...")
    while True:
        tasks = get_tasks()
        if isinstance(tasks, list) and tasks:
            for task in tasks:
                t_row = task.get('row')
                if not t_row: continue
                print(f"⏳ Processing Row {t_row}...")
                update_task(t_row, {"status": "Pending"})
                res = ai_post_production("Video", "General", task.get('script'))
                if res:
                    res["status"] = "Done"
                    update_task(t_row, res)
                    print(f"✅ Row {t_row} Done with AI Image Link!")
                else:
                    update_task(t_row, {"status": "Create"})
                    print(f"❌ Row {t_row} Failed.")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()
