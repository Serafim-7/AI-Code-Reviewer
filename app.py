import os
import json
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    print("⚠️  Warning: OPENAI_API_KEY not set! The API will fail without it.")

def build_prompt(language, code, filename=None):
    return f"""
You are an expert software engineer and code reviewer.
Review the following {language or 'code'} file.

Provide your response in pure JSON format with:
- summary: short text
- findings: list of {{line, severity, issue, suggestion}}
- improvements: general advice

Filename: {filename or 'unknown'}
---
{code}
"""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/review", methods=["POST"])
def review_code():
    data = request.json
    code = data.get("code")
    language = data.get("language", "unknown")
    filename = data.get("filename")

    if not code:
        return jsonify({"error": "No code provided"}), 400

    prompt = build_prompt(language, code, filename)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a code reviewer that outputs JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 800
    }

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            return jsonify(parsed)
        except json.JSONDecodeError:
            return jsonify({"raw_response": content, "note": "Response was not valid JSON"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
