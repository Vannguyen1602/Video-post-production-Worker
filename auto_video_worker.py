import requests
import json
import time
import os
import re
from google import genai
from google.genai import types

# --- CONFIGURATION ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxeBKabG7Ecfig2WXNrP5o_k8F7TV8hhENA6JW03QgslWt-1pPguUoUwyCl10tncOAb/exec"
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
    """Cập nhật dữ liệu và trạng thái về Google Sheet."""
    payload = {
        "action": "update_task",
        "row": task_row,
        **data
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        return response.status_code == 200
    except: return False

def ai_post_production(topic, subtopic, script_content):
    """AI Post-Production v5.2 (Optimized Strategy)."""
    prompt = f"""
    You are a World-Class Social Media Strategist. 
    TASK: Process content for a video.
    TOPIC: "{topic}"
    SUBTOPIC: "{subtopic}"
    SCRIPT: {script_content}

    RULES (ALL ENGLISH):
    1. CAPTION (FB/IG/YT): Universal Hook < 125 chars. 3-5 lines body. CTA: Comment keyword.
    2. CAPTION TIKTOK: 1 Hook + 1 CTA. No filler. 
    3. HASHTAGS: 3-5 per platform. TikTok total length < 150 (Cap+Tags).
    4. YOUTUBE TITLE: Golden 60 chars. [SEO] + (Emotional Hook). Year 2026.
    5. THUMBNAIL: Animation style. Illustrate core script concept. Bold catchy Title on image. No State names.

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
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        text = response.text
        def extract(tag):
            match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
            return match.group(1).strip() if match else ""

        return {
            "caption": extract("CAPTION_GENERAL"),
            "caption_tiktok": extract("CAPTION_TIKTOK"),
            "hashtag_tiktok": extract("HASHTAG_TIKTOK"),
            "hashtag_facebook": extract("HASHTAG_FACEBOOK"),
            "hashtag_youtube": extract("HASHTAG_YOUTUBE"),
            "hashtag_instagram": extract("HASHTAG_INSTAGRAM"),
            "title youtube": extract("TITLE_YOUTUBE"),
            "thumbnail": extract("THUMBNAIL_PROMPT")
        }
    except: return None

def run_worker():
    print("🤖 Video Factory Worker v5.2 (Logic: Pending -> Done) started...")
    while True:
        tasks_data = get_tasks()
        
        if isinstance(tasks_data, dict) and tasks_data.get("error") == "No tasks":
            print("😴 No 'Create' tasks found.")
            tasks = []
        elif isinstance(tasks_data, list):
            tasks = tasks_data
        else:
            tasks = []

        if tasks:
            print(f"Found {len(tasks)} tasks!")
            for task in tasks:
                t_row = task.get('row') or task.get('id')
                if not t_row: continue
                
                topic = task.get('topic') or task.get('Topic') or 'General'
                subtopic = task.get('subtopic') or task.get('Subtopic') or 'N/A'
                script = task.get('script') or task.get('Script') or ''
                
                # BƯỚC 1: CHUYỂN SANG PENDING
                print(f"⏳ Setting Row {t_row} to PENDING...")
                update_task(t_row, {"status": "Pending"})
                
                # BƯỚC 2: XỬ LÝ AI
                print(f"🧠 Processing AI for Row {t_row}: {topic}...")
                processed_data = ai_post_production(topic, subtopic, script)
                
                if processed_data:
                    # BƯỚC 3: ĐẨY DỮ LIỆU VÀ CHUYỂN SANG DONE
                    processed_data["status"] = "Done"
                    if update_task(t_row, processed_data):
                        print(f"✅ Row {t_row} COMPLETED (Done).")
                    else:
                        print(f"❌ Failed to push result for Row {t_row}.")
                else:
                    # NẾU LỖI THÌ TRẢ VỀ CREATE ĐỂ LẦN SAU THỬ LẠI
                    update_task(t_row, {"status": "Create"})
                    print(f"⚠️ AI Error. Reverted Row {t_row} to Create.")
        
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()
