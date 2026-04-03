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
INTERVAL_SECONDS = 60 # Kiểm tra sheet mỗi 1 phút

# --- AI CLIENT ---
client = genai.Client(api_key=GEMINI_API_KEY)

def get_tasks():
    """Lấy danh sách task từ Google Sheet."""
    try:
        response = requests.get(WEBHOOK_URL, params={"action": "get_tasks"}, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error getting tasks: {e}")
        return []

def update_task(task_id, caption, hashtags, thumbnail_prompt):
    """Cập nhật kết quả về Google Sheet (Gửi Prompt cho KIE AI)."""
    payload = {
        "action": "update_task",
        "id": task_id,
        "caption": caption,
        "hashtags": hashtags,
        "thumbnail": thumbnail_prompt, # Gửi PROMPT để KIE AI vẽ
        "status": "Done"
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Error updating task {task_id}: {e}")
        return False

def ai_post_production(topic, subtopic, state_name):
    """Sử dụng Gemini AI để tạo Prompt cho KIE AI."""
    prompt = f"""
    You are an Expert Video Post-Production Specialist.
    TASK: Process content for a TikTok/Reels video about DMV Driver Manual for the state of {state_name}.
    TOPIC: {topic}
    SUBTOPIC: {subtopic}

    RULES:
    1. CAPTION: Hook the audience, very engaging. DO NOT include hashtags inside the caption. Use Vietnamese.
    2. HASHTAGS: Only English hashtags, highly relevant to DMV, {state_name}, and driving tests. (At least 10 hashtags).
    3. THUMBNAIL PROMPT (FOR KIE AI):
       - Characters: Guider (Rectangular head, sharp nose, black suit, red tie/badge) and Student (Round head, spiky hair, striped socks).
       - Interaction: Dynamic and funny interaction related to the topic "{topic}".
       - Expressions: Funny, exaggerated reactions (surprised, happy, or thinking hard).
       - Context: Visual illustration of the driving rule in {state_name}.
       - Style: 2D Flat vector art, bold outlines, vibrant colors, satirical animated vibe, high contrast.
       - Title Text: Extract a shock/catchy title from the content for the thumbnail.

    OUTPUT FORMAT (XML TAGS):
    <CAPTION>...</CAPTION>
    <HASHTAGS>...</HASHTAGS>
    <THUMBNAIL_PROMPT>...</THUMBNAIL_PROMPT>
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        text = response.text
        
        caption = re.search(r'<CAPTION>(.*?)</CAPTION>', text, re.DOTALL).group(1).strip()
        hashtags = re.search(r'<HASHTAGS>(.*?)</HASHTAGS>', text, re.DOTALL).group(1).strip()
        thumb = re.search(r'<THUMBNAIL_PROMPT>(.*?)</THUMBNAIL_PROMPT>', text, re.DOTALL).group(1).strip()
        
        return caption, hashtags, thumb
    except Exception as e:
        print(f"AI Error: {e}")
        return None, None, None

def run_worker():
    print("🤖 Video Factory Worker (KIE AI Mode) started...")
    while True:
        tasks = get_tasks()
        if tasks:
            print(f"Found {len(tasks)} tasks to process!")
            for task in tasks:
                t_id = task.get('id')
                topic = task.get('topic', 'DMV Practice Test')
                subtopic = task.get('subtopic', 'General Knowledge')
                state = task.get('state', 'USA')
                
                print(f"Processing Task {t_id}: {state} - {topic}...")
                cap, tags, thumb_prompt = ai_post_production(topic, subtopic, state)
                
                if cap and tags and thumb_prompt:
                    if update_task(t_id, cap, tags, thumb_prompt):
                        print(f"✅ Task {t_id} completed and pushed to Sheet.")
                    else:
                        print(f"❌ Failed to update Task {t_id} on Sheet.")
                else:
                    print(f"⚠️ Failed to process Task {t_id} with AI.")
        else:
            print("😴 No tasks found. Sleeping...")
            
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()
