import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import urllib.parse as urlparse
import PyPDF2
import requests
from bs4 import BeautifulSoup
from PIL import Image

app = Flask(__name__)
# CORS zaroori hai taaki Vercel (Frontend) se Render (Backend) par request aa sake
CORS(app)

# Apni Gemini API key yahan set karein (Render environment variables me GEMINI_API_KEY honi chahiye)
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# Gemini 1.5 Flash sabse fast aur best hai notes aur images ke liye
model = genai.GenerativeModel('gemini-1.5-flash')

# Master Prompt jo har baar AI ko direction dega
MASTER_PROMPT = """
You are 'SmartAI Tutor', an expert teacher. Create highly engaging, topper-level study notes based ONLY on the provided content. 
Structure your response exactly like this:
1. Short Summary
2. Key Concepts & Definitions (with bullet points)
3. A detailed Mermaid Mindmap (wrap it in ```mermaid ... ```)
4. 3 Important MCQs with answers at the bottom.

Do not make up facts. If the content is short, explain it simply.
Here is the content:
"""

@app.route('/')
def home():
    return "SmartAI Server is Awake and Running 100%!"

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        mode = request.form.get('mode')
        content = request.form.get('content', '')
        
        text_for_ai = ""
        image_for_ai = None

        # 1. TOPIC MODE
        if mode == 'topic':
            text_for_ai = content

        # 2. TEXT MODE
        elif mode == 'text':
            text_for_ai = content

        # 3. YOUTUBE MODE (100% Fixed)
        elif mode == 'youtube':
            try:
                # Extract Video ID
                parsed_url = urlparse.urlparse(content)
                video_id = urlparse.parse_qs(parsed_url.query).get('v')
                if video_id:
                    video_id = video_id[0]
                else:
                    video_id = content.split('v=')[-1] # Fallback
                
                # Fetch Subtitles
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                text_for_ai = " ".join([d['text'] for d in transcript_list])
                
            except Exception as e:
                return jsonify({'status': 'error', 'error': 'Is video me Subtitles (CC) nahi hain ya link galat hai. AI ko padhne ke liye subtitles chahiye!'})

        # 4. URL/WEBSITE MODE
        elif mode == 'url':
            try:
                res = requests.get(content, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(res.text, 'html.parser')
                # Sirf paragraphs (p tags) ka text nikalenge taaki kachra na aaye
                paragraphs = soup.find_all('p')
                text_for_ai = " ".join([p.get_text() for p in paragraphs])
            except Exception as e:
                return jsonify({'status': 'error', 'error': 'Website se data nahi nikal paya. Security ho sakti hai.'})

        # 5. PDF FILE MODE
        elif mode == 'file':
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'error': 'No file uploaded'})
            file = request.files['file']
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_for_ai += page.extract_text() + "\n"
            except Exception as e:
                return jsonify({'status': 'error', 'error': 'PDF padhne mein error aayi. Shayad file locked hai.'})

        # 6. CAMERA / IMAGE MODE
        elif mode == 'image':
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'error': 'No image found'})
            file = request.files['file']
            try:
                image_for_ai = Image.open(file)
            except Exception as e:
                return jsonify({'status': 'error', 'error': 'Image open nahi ho saki.'})

        # ==========================================
        # FINAL STEP: Send Data to Gemini AI
        # ==========================================
        if image_for_ai:
            # Agar image hai toh image + prompt bhejenge
            response = model.generate_content([MASTER_PROMPT, image_for_ai])
        elif text_for_ai.strip() != "":
            # Agar text hai toh text + prompt bhejenge
            # Text limit set kar dete hain taaki API crash na ho (approx 30,000 chars)
            final_prompt = MASTER_PROMPT + "\n\n" + text_for_ai[:30000]
            response = model.generate_content(final_prompt)
        else:
            return jsonify({'status': 'error', 'error': 'Mujhe padhne ke liye kuch text nahi mila!'})

        return jsonify({'status': 'success', 'summary': response.text})

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Server mein koi technical dikkat aayi hai. Try again.'})


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        context = data.get('context', '')
        question = data.get('question', '')

        if not question:
            return jsonify({'status': 'error', 'error': 'Please ask a question.'})

        chat_prompt = f"Context Notes: {context}\n\nStudent's Doubt: {question}\n\nAnswer the student's doubt clearly and politely in Hinglish or English based on the context provided. Keep it helpful."
        
        response = model.generate_content(chat_prompt)
        return jsonify({'status': 'success', 'answer': response.text})

    except Exception as e:
        return jsonify({'status': 'error', 'error': 'Chat bot abhi busy hai.'})

if __name__ == '__main__':
    # Render ke liye port 10000 ya environment port use karna zaroori hai
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
