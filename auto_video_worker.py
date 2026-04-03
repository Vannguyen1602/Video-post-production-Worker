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

def ai_post_production(topic, subtopic, script_content):
    """AI Post-Production v5.5 (KIE Prompt Generation Mode)."""
    
    prompt = f"""
    You are a World-Class Social Media Strategist. 
    TASK: Process content for a video based on the Script.
    SCRIPT: {script_content}

    RULES (ALL OUTPUT MUST BE IN ENGLISH):
    1. CAPTION (FB/IG/YT): Universal Hook < 125 chars. 3-5 lines body. CTA: Comment keyword.
    2. CAPTION TIKTOK: 1 Hook + 1 CTA. No filler. 
    3. HASHTAGS: 3-5 per platform. 
    4. YOUTUBE TITLE: Golden 60 chars. [SEO Keywords] + (Emotional Hook). Year 2026.
    5. THUMBNAIL (KIE AI PROMPT): 
       - Style: Professional 2D Animation style, vibrant colors, high contrast.
       - Content: MUST illustrate the core concept of the script.
       - Text: MUST include a very bold, catchy Title text on the image.
       - Characters: If the script suggests Guider/Student, include them. 
       - Style Note: Satirical animated vibe, prominent visual storytelling.

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
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def run_worker():
    print("🤖 Video Factory Worker v5.5 (KIE Prompt Mode) started...")
    while True:
        tasks = get_tasks()
        if isinstance(tasks, list) and tasks:
            for task in tasks:
                t_row = task.get('row')
                if not t_row: continue
                
                print(f"⏳ Processing Row {t_row} (Generating Content + KIE Prompt)...")
                update_task(t_row, {"status": "Pending"})
                
                res = ai_post_production("Video", "General", task.get('script'))
                
                if res:
                    res["status"] = "Done"
                    if update_task(t_row, res):
                        print(f"✅ Row {t_row} Done with KIE Prompt!")
                    else:
                        print(f"❌ Failed to update Row {t_row}.")
                else:
                    update_task(t_row, {"status": "Create"})
                    print(f"❌ AI process failed for Row {t_row}.")
        
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()
