import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import urllib.parse as urlparse
import PyPDF2
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# ==========================================
# 🟢 GROK API SETUP 🟢
# ==========================================
API_KEY = os.environ.get("GROK_API_KEY") 

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.x.ai/v1",
)

GROK_MODEL = "grok-beta"

MASTER_PROMPT = """
You are 'SmartAI Tutor', an expert teacher. Create highly engaging, topper-level study notes based ONLY on the provided content. 
Structure your response exactly like this:
1. Short Summary
2. Key Concepts & Definitions (with bullet points)
3. A detailed Mermaid Mindmap (wrap it in ```mermaid ... ```)
4. 3 Important MCQs with answers at the bottom.

Do not make up facts. If the content is short, explain it simply.
"""

@app.route('/')
def home():
    return "SmartAI (Grok Edition) Server is Awake and Running 100%!"

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        mode = request.form.get('mode')
        content = request.form.get('content', '')
        
        text_for_ai = ""

        # 1. TOPIC & TEXT MODE
        if mode in ['topic', 'text']:
            text_for_ai = content

        # 2. YOUTUBE MODE (With Smart Fallback)
        elif mode == 'youtube':
            try:
                parsed_url = urlparse.urlparse(content)
                video_id = urlparse.parse_qs(parsed_url.query).get('v')
                if not video_id:
                    video_id = content.split('v=')[-1].split('&')[0].split('?')[0].split('/')[-1]
                
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                text_for_ai = " ".join([d['text'] for d in transcript_list])
                
            except Exception:
                try:
                    ydl_opts = {'quiet': True, 'skip_download': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(content, download=False)
                        title = info.get('title', 'Unknown Title')
                        desc = info.get('description', '')
                        text_for_ai = f"Video Title: {title}\n\nVideo Description: {desc}\n\nMake notes based on this information."
                except Exception:
                    return jsonify({'status': 'error', 'error': 'Is video ka data private hai. AI isko nahi padh sakta.'})

        # 3. URL/WEBSITE MODE
        elif mode == 'url':
            try:
                res = requests.get(content, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(res.text, 'html.parser')
                paragraphs = soup.find_all('p')
                text_for_ai = " ".join([p.get_text() for p in paragraphs])
            except Exception:
                return jsonify({'status': 'error', 'error': 'Website ki security ne data nikalne se rok diya hai.'})

        # 4. PDF FILE MODE
        elif mode == 'file':
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'error': 'No file uploaded'})
            file = request.files['file']
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_for_ai += page.extract_text() + "\n"
            except Exception:
                return jsonify({'status': 'error', 'error': 'PDF padhne mein error aayi. Shayad file locked hai.'})

        # 5. CAMERA / IMAGE MODE 
        elif mode == 'image':
            return jsonify({'status': 'error', 'error': 'Image mode abhi maintainance mein hai. Kripya PDF ya Topic try karein.'})

        # ==========================================
        # FINAL STEP: Send Data to Grok AI
        # ==========================================
        if text_for_ai and text_for_ai.strip() != "":
            response = client.chat.completions.create(
                model=GROK_MODEL,
                messages=[
                    {"role": "system", "content": MASTER_PROMPT},
                    {"role": "user", "content": f"Here is the content to summarize:\n{text_for_ai[:30000]}"}
                ]
            )
            summary = response.choices[0].message.content
            return jsonify({'status': 'success', 'summary': summary})
        else:
            return jsonify({'status': 'error', 'error': 'Mujhe padhne ke liye kuch text nahi mila!'})

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({'status': 'error', 'error': f'Server Error: API key missing ya invalid ho sakti hai.'})


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        context = data.get('context', '')
        question = data.get('question', '')

        if not question:
            return jsonify({'status': 'error', 'error': 'Please ask a question.'})

        chat_prompt = f"Context Notes: {context}\n\nStudent's Doubt: {question}\n\nAnswer the student's doubt clearly and politely in Hinglish or English based on the context provided."
        
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": chat_prompt}
            ]
        )
        answer = response.choices[0].message.content
        return jsonify({'status': 'success', 'answer': answer})

    except Exception:
        return jsonify({'status': 'error', 'error': 'Chat bot abhi busy hai.'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
