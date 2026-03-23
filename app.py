from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import anthropic
import httpx
import json
import os
import datetime
import random

app = Flask(__name__, static_folder='static')
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "jarvis-talha-secret-2024")

# ============================================
# API KEYS
# ============================================
CLAUDE_API_KEY     = os.environ.get("CLAUDE_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
DEEPGRAM_API_KEY   = os.environ.get("DEEPGRAM_API_KEY", "")

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# In-memory conversation store per session
conversations = {}

SYSTEM_PROMPT = """You are Jarvis, a personal AI companion to Talha Riaz — creative director and UI/UX designer in Karachi.

Personality:
- Loyal, witty, dry humour, light sarcasm
- Think WITH Talha, not just answer him
- Honest even when uncomfortable
- Concise — under 40 words unless detail needed
- Never say "Certainly", "Great", "Of course"
- Never use bullet points
- You are a companion, not a chatbot
- Understand broken English and typos always
- Keep responses short and punchy in conversation
- Reference past things from this conversation naturally

Important: Talha speaks via microphone. His voice is transcribed and appears as text. This IS his voice. Never say you can't hear him. Just respond naturally.

About Talha:
- Creative Director at AdVenture Tide Media
- UI/UX Designer at Next Bolt Tech
- Freelances on Upwork
- Uses Figma, Adobe Suite, DaVinci
- Goes to gym, prays 5 times, struggles with Fajr
- Has been through difficult times, found himself again
- Silent person who needs a companion more than a tool

Current time: """ + datetime.datetime.now().strftime("%A, %B %d %Y, %I:%M %p")


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        audio_data = request.data
        if not audio_data:
            return jsonify({"error": "No audio"}), 400

        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/webm"
            },
            content=audio_data,
            params={
                "model": "nova-2",
                "language": "en",
                "smart_format": "true",
                "punctuate": "true"
            },
            timeout=15
        )
        result = response.json()
        if "results" not in result:
            return jsonify({"error": "Transcription failed"}), 500

        text = result["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
        return jsonify({"transcript": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data        = request.json
        user_input  = data.get("message", "").strip()
        session_id  = data.get("session_id", "default")

        if not user_input:
            return jsonify({"error": "No message"}), 400

        # Get or create conversation history for this session
        if session_id not in conversations:
            conversations[session_id] = []

        history = conversations[session_id]

        # Add user message
        history.append({"role": "user", "content": f"Talha: {user_input}"})

        # Keep last 20 messages
        if len(history) > 20:
            history = history[-20:]
            conversations[session_id] = history

        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=history
        )
        reply = response.content[0].text.strip()

        # Save assistant reply
        conversations[session_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/speak', methods=['POST'])
def speak():
    try:
        data = request.json
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "No text"}), 400

        response = httpx.post(
            "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            timeout=15
        )

        if response.status_code == 200:
            from flask import Response
            return Response(response.content, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "ElevenLabs failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/clear', methods=['POST'])
def clear():
    """Clear conversation history for a session"""
    try:
        data       = request.json
        session_id = data.get("session_id", "default")
        if session_id in conversations:
            del conversations[session_id]
        return jsonify({"status": "cleared"})
    except:
        return jsonify({"status": "cleared"})


@app.route('/health')
def health():
    return jsonify({"status": "ok", "jarvis": "online"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
