import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup
import io
from openai import OpenAI
from PIL import Image
import pytesseract
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
CORS(app)

# --- 100% SECURE GROQ API CONFIGURATION ---
# ⚠️ WARNING: DO NOT PASTE YOUR 'gsk_' KEY HERE! ⚠️
# Render.com par 'Environment Variables' mein apni key daalni hai.
API_KEY = os.getenv("GROQ_API_KEY") 

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def ask_ai(system_prompt, user_prompt):
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    last_error = ""
    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_name, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            continue
    return f"Error: All models busy. Last error: {last_error}"

@app.route('/api/summarize', methods=['POST'])
def analyze_content():
    mode = request.form.get('mode')
    raw_text = ""
    topic = ""

    try:
        # Agar Render par key set nahi ki, toh ye error dega
        if not API_KEY:
            return jsonify({'error': 'Server configuration error: API Key not found. Please set GROQ_API_KEY in Render.'}), 500

        if mode == 'topic':
            topic = request.form.get('content', '')
            if not topic: return jsonify({'error': 'Please enter a topic name.'}), 400
            raw_text = topic 
        elif mode == 'text': raw_text = request.form.get('content', '')
        elif mode == 'url':
            headers = {'User-Agent': 'Mozilla/5.0'}
            soup = BeautifulSoup(requests.get(request.form.get('content', ''), headers=headers).text, 'lxml')
            raw_text = " ".join([p.get_text() for p in soup.find_all('p')])
        elif mode == 'file':
            pdf_reader = PdfReader(io.BytesIO(request.files['file'].read()))
            for page in pdf_reader.pages: raw_text += page.extract_text() + " "
        elif mode == 'youtube':
            url = request.form.get('content', '')
            video_id = url.split('v=')[-1].split('&')[0] if 'v=' in url else url.split('/')[-1].split('?')[0]
            raw_text = " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(video_id)])
        elif mode == 'image':
            img = Image.open(request.files['file'].stream)
            raw_text = pytesseract.image_to_string(img)

        if not raw_text.strip(): return jsonify({'error': 'Could not extract text.'}), 400

        # --- THE TOPPER'S MASTER PROMPT ---
        system_p = "You are an elite AI Study Professor creating modules for top-tier competitive exams. Provide extreme conceptual depth, logical breakdowns, and professional Markdown formatting. Do not hallucinate."
        
        prompt = f"""Deeply analyze this content/topic: '{raw_text[:12000]}'

        Create a 'Topper-Level' comprehensive study guide. STRICTLY use this Markdown format:

        # 🌟 The Master Study Guide
        > *Write a highly engaging hook, real-world application, or historical context about this topic.*

        ## 📖 1. Advanced Detailed Explanation
        (Dive incredibly deep into the core concepts. Explain the 'Why' and 'How' with step-by-step logic. If applicable, explain the mechanisms, derivations, or advanced theories. Break text into highly readable paragraphs. **Bold** critical terms.)

        ## ⚡ 2. The Ultimate Cheat Sheet (Deep Formulas, Rules & Pro-Tricks)
        (Create a heavily organized bulleted list of all critical formulas, equations, methods, and principles. Include specific **'Pro-Tips'**, **'Mnemonics (Memory Tricks)'**, and common mistakes to avoid. Make this the ultimate quick-revision asset.)

        ## 🧠 3. Visual Concept Mindmap
        (You MUST create a valid Mermaid.js flowchart graph to represent the hierarchy of these concepts visually. Wrap it EXACTLY in a ```mermaid code block. Do NOT use standard text bullets here.)
        ```mermaid
        graph TD
            A[Main Topic] --> B[Core Concept 1]
            A --> C[Core Concept 2]
            B --> D[Important Detail]
            C --> E[Formula/Rule]
            style A fill:#3b82f6,stroke:#fff,stroke-width:2px,color:#fff
        ```

        ## 🏆 4. Master Challenge (8 MCQs)
        (Generate 8 extremely conceptual, application-based MCQs. Do not provide answers here.)
        **Q1. [Question Text]**
        - A) [Option]
        - B) [Option]
        - C) [Option]
        - D) [Option]
        *(Repeat for Q2 to Q8)*

        ---
        ## 🔑 Answer Key
        (ONLY provide the correct letter: Q1: A, Q2: C, etc.)
        """
        
        result = ask_ai(system_p, prompt)
        return jsonify({'status': 'success', 'summary': result})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def solve_doubt():
    data = request.json
    context = data.get('context', '')
    question = data.get('question', '')
    
    system_p = "You are an advanced AI Tutor. Break down the student's doubt with step-by-step logic based on the study notes context."
    user_p = f"STUDY NOTES CONTEXT:\n{context}\n\nSTUDENT'S DOUBT: {question}"
    
    return jsonify({'status': 'success', 'answer': ask_ai(system_p, user_p)})

if __name__ == '__main__':
    print("🚀 SECURE MASTER AI Backend Running...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
