import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai # 👈 Naya Google Package
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import urllib.parse as urlparse
import PyPDF2
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# ==========================================
# 🟢 NAYA GEMINI API SETUP (google-genai) 🟢
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Naya Client Setup
client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)

# Naya Model Name
GEMINI_MODEL = 'gemini-2.0-flash'

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
    return "SmartAI (New Gemini GenAI Edition) Server is Awake and Running 100%!"

@app.route('/api/summarize', methods=['POST'])
def summarize():
    if not client:
        return jsonify({'status': 'error', 'error': 'Render Dashboard par GEMINI_API_KEY set nahi hai!'})

    try:
        mode = request.form.get('mode')
        content = request.form.get('content', '')
        
        text_for_ai = ""

        if mode in ['topic', 'text']:
            text_for_ai = content

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
                    return jsonify({'status': 'error', 'error': 'Is video ka data private hai ya CC nahi hai.'})

        elif mode == 'url':
            try:
                res = requests.get(content, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(res.text, 'html.parser')
                paragraphs = soup.find_all('p')
                text_for_ai = " ".join([p.get_text() for p in paragraphs])
            except Exception:
                return jsonify({'status': 'error', 'error': 'Website ki security ne data nikalne se rok diya hai.'})

        elif mode == 'file':
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'error': 'No file uploaded'})
            file = request.files['file']
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_for_ai += page.extract_text() + "\n"
            except Exception:
                return jsonify({'status': 'error', 'error': 'PDF padhne mein error aayi.'})

        elif mode == 'image':
            return jsonify({'status': 'error', 'error': 'Image mode abhi maintainance mein hai.'})

        # ==========================================
        # FINAL STEP: Send Data to New Gemini AI
        # ==========================================
        if text_for_ai and text_for_ai.strip() != "":
            final_prompt = MASTER_PROMPT + "\n\nContent:\n" + text_for_ai[:30000]
            
            # Naya API Call Syntax
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=final_prompt,
            )
            return jsonify({'status': 'success', 'summary': response.text})
        else:
            return jsonify({'status': 'error', 'error': 'Mujhe padhne ke liye kuch text nahi mila!'})

    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API Error: {error_msg}")
        return jsonify({'status': 'error', 'error': 'AI API ne error diya hai. Shayad rate limit cross ho gayi.'})

@app.route('/api/chat', methods=['POST'])
def chat():
    if not client:
        return jsonify({'status': 'error', 'error': 'API Key Missing!'})

    try:
        data = request.get_json()
        context = data.get('context', '')
        question = data.get('question', '')

        if not question:
            return jsonify({'status': 'error', 'error': 'Please ask a question.'})

        chat_prompt = f"Context Notes: {context}\n\nStudent's Doubt: {question}\n\nAnswer the student's doubt clearly and politely in Hinglish or English based on the context provided."
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=chat_prompt,
        )
        return jsonify({'status': 'success', 'answer': response.text})

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Chat bot abhi busy hai.'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
