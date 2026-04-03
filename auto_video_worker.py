import requests
import json
import time
import os
import re
from google import genai
from google.genai import types

# --- CONFIGURATION ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycxvo8PlYnz2MeKTltiPDNBr8uihoxy583YGECG4F5p0BLKQRQ7Q1PcXdEp8qSeIPjvfSA/exec"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERVAL_SECONDS = 60 

# --- AI CLIENT ---
client = genai.Client(api_key=GEMINI_API_KEY)

def get_tasks():
    try:
        response = requests.get(WEBHOOK_URL, params={"action": "get_tasks"}, timeout=30)
        return response.json() if response.status_code == 200 else []
    except: return []

def update_task(task_id, data):
    """Cập nhật toàn bộ các cột mới về Google Sheet."""
    payload = {
        "action": "update_task",
        "id": task_id,
        "status": "Done",
        **data
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        return response.status_code == 200
    except: return False

def ai_post_production(topic, subtopic, script_content):
    """Quy trình AI Post-Production mới nhất (Đa nền tảng + Tối ưu Viral)."""
    prompt = f"""
    You are a World-Class Social Media Strategist and Video Editor. 
    TASK: Process content for a video based on this topic: "{topic}" and subtopic: "{subtopic}".
    SCRIPT CONTENT: {script_content}

    RULES (ALL OUTPUT MUST BE IN ENGLISH):

    1. CAPTION (FB/IG/YT): 
       - Line 1-2 (The Hook): Max 125 chars. Must include main keywords and curiosity.
       - Body: 3-5 lines max. Use bullet points and emojis (✅, 💡, 🚀, 🎯).
       - Universal CTA: Do NOT include links. Ask users to comment a specific keyword to get the link/resource.
    
    2. CAPTION TIKTOK:
       - Format: 1 Hook sentence + 1 CTA sentence.
       - Tone: Direct, energetic, no filler. Max 1-2 emojis.
    
    3. HASHTAGS (3-5 per platform, niche-specific):
       - TikTok: Must be short. (Note: TikTok Caption + Hashtags must be < 150 chars total).
       - Facebook, YouTube, Instagram: Separate lists.

    4. YOUTUBE TITLE:
       - Max 100 chars, but front-load most important info in first 60 chars.
       - Format: [SEO Keywords] + (Emotional Hook / Value Promise).
       - Include year "2026". Use Power Words (Latest, Secret, Hack, Mistake).
       - Visual Formatting: Use [ ], ( ), or |.

    5. THUMBNAIL PROMPT (KIE AI):
       - Style: Professional 2D Animation style. 
       - Content: Illustrate the core concept of the script. Do NOT mention any US State names.
       - Focus: Prominent, catchy, and bold Title Text on the image. High contrast, vibrant colors.

    OUTPUT FORMAT (XML TAGS):
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

        data = {
            "caption": extract("CAPTION_GENERAL"),
            "caption_tiktok": extract("CAPTION_TIKTOK"),
            "hashtag_tiktok": extract("HASHTAG_TIKTOK"),
            "hashtag_facebook": extract("HASHTAG_FACEBOOK"),
            "hashtag_youtube": extract("HASHTAG_YOUTUBE"),
            "hashtag_instagram": extract("HASHTAG_INSTAGRAM"),
            "Titile youtube": extract("TITLE_YOUTUBE"), # Matching sheet column name spelling
            "thumbnail": extract("THUMBNAIL_PROMPT")
        }
        
        # Validation: TikTok limit
        if len(data["caption_tiktok"]) + len(data["hashtag_tiktok"]) > 145:
            data["caption_tiktok"] = data["caption_tiktok"][:100] + "..."
            
        return data
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def run_worker():
    print("🤖 Video Factory Worker v5.0 (Multi-Platform Strategist) started...")
    while True:
        tasks = get_tasks()
        if tasks:
            print(f"Found {len(tasks)} tasks to process!")
            for task in tasks:
                t_id = task.get('id')
                topic = task.get('topic', 'General')
                subtopic = task.get('subtopic', 'General')
                script = task.get('script', '') # Assuming script is provided in task
                
                print(f"Processing Task {t_id}: {topic}...")
                processed_data = ai_post_production(topic, subtopic, script)
                
                if processed_data:
                    if update_task(t_id, processed_data):
                        print(f"✅ Task {t_id} optimized for all platforms and pushed.")
                    else:
                        print(f"❌ Failed to update Task {t_id}.")
        else:
            print("😴 Waiting for 'Create' status on Sheet...")
            
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()
