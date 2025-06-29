from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import traceback
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
import tempfile
import re

app = Flask(__name__)
CORS(app)

# Groq API Configuration
# GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# ==============================
# Topic Prompts
# ==============================
topic_prompts = {
    topic: """
You are a CLAT critical reasoning test generator.
Generate a passage of 500–600 words in a formal academic tone. Use numbered paragraphs.
The passage should contain logical arguments, assumptions, and flaws — not factual content.

Then add the heading: **MCQs**

Create 5 multiple-choice questions (numbered 1 to 5).
Each question should have 4 options labeled (A), (B), (C), (D). Only one correct.

After each question, include:
Answer: (correct option)
Explanation: short explanation of why it is correct.

Structure:
1. Question?
(A) Option 1
(B) Option 2
(C) Option 3
(D) Option 4
Answer: (C)
Explanation: ...

Only follow this format strictly. Do not include any other headings.
""" for topic in [
        "Reading Comprehension", "Grammar", "Vocabulary", "Para Jumbles", "Critical Reasoning",
        "Logical Reasoning", "Analytical Reasoning", "Puzzles", "Syllogisms",
        "Legal Reasoning", "Constitutional Law", "Contract Law", "Tort Law",
        "Criminal Law", "Legal Principles", "Legal Maxims",
        "Arithmetic", "Algebra", "Geometry", "Data Interpretation", "Percentages", "Profit & Loss",
        "General Knowledge", "Current Affairs", "History", "Geography",
        "Politics", "Economics", "Science & Technology", "Sports", "Awards & Honours"
    ]
}

# ==============================
# Helper Functions
# ==============================

def call_groq_api(messages, temperature=0.7, max_tokens=4000):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return None

def generate_study_material(topic, count):
    all_sections = []
    for i in range(count):
        print(f"📝 Generating section {i+1}/{count} for {topic}...")
        prompt = topic_prompts.get(topic, f"Generate a CLAT-level {topic} test with passage, questions, and answer key.")
        messages = [
            {"role": "system", "content": "You are an expert CLAT study material generator."},
            {"role": "user", "content": prompt}
        ]
        result = call_groq_api(messages)
        if result:
            all_sections.append(f"Topic: {topic}\n\n{result.strip()}")
        else:
            print(f"❌ Failed to generate section {i+1}")
    return all_sections

def parse_mcqs(raw_text):
    parts = re.split(r'\*\*MCQs\*\*', raw_text)
    if len(parts) < 2:
        return []

    passage = parts[0].strip()
    mcqs_text = parts[1].strip()

    question_blocks = re.findall(r'(\d+\..*?)(?=\n\d+\.|\Z)', mcqs_text, re.DOTALL)
    structured_questions = []

    for idx, block in enumerate(question_blocks, start=1):
        try:
            q_match = re.search(r'\d+\.\s*(.+?)\n\(A\)', block, re.DOTALL)
            question = q_match.group(1).strip() if q_match else "Unknown question"

            options = []
            for opt in ['A', 'B', 'C', 'D']:
                opt_match = re.search(rf'\({opt}\)\s*(.+)', block)
                options.append(opt_match.group(1).strip() if opt_match else f"Option {opt}")

            ans_match = re.search(r'Answer:\s*\(([A-D])\)', block)
            correct_letter = ans_match.group(1) if ans_match else 'A'
            correct_index = ord(correct_letter) - ord('A')

            exp_match = re.search(r'Explanation:\s*(.+)', block, re.DOTALL)
            explanation = exp_match.group(1).strip() if exp_match else "Explanation not available"

            structured_questions.append({
                "id": idx,
                "passage": passage,
                "question": question,
                "options": options,
                "correct": correct_index,
                "explanation": explanation
            })
        except Exception as e:
            print(f"[ERROR PARSING Q{idx}]: {e}")
            continue

    return structured_questions

def create_pdf(contents, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    try:
        font_path = "DejaVuSans.ttf"
        if os.path.exists(font_path):
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", size=12)
        else:
            pdf.set_font("Arial", size=12)
    except:
        pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln()
    for section in contents:
        try:
            clean = section.encode('latin1', 'replace').decode('latin1')
        except:
            clean = section
        pdf.multi_cell(0, 10, clean)
        pdf.ln()
    return BytesIO(pdf.output(dest='S').encode('latin1'))

# ==============================
# Routes
# ==============================

@app.route("/generate-test", methods=['POST'])
def generate_content():
    try:
        data = request.get_json()
        topic = data.get('topic') or data.get('subcategory')
        if topic:
            topic = topic.replace("-", " ").title()
        else:
            return jsonify({'error': 'Topic is missing'}), 400

        count = data.get('count', 1)
        if topic not in topic_prompts:
            return jsonify({'error': f"Invalid topic. Available: {list(topic_prompts.keys())}"}), 400
        if not isinstance(count, int) or not (1 <= count <= 5):
            return jsonify({'error': 'Count must be an integer between 1 and 5'}), 400

        sections = generate_study_material(topic, count)
        if not sections:
            return jsonify({'error': 'Generation failed'}), 500

        structured = parse_mcqs(sections[0])
        if not structured:
            print("\n[DEBUG] Raw output:\n", sections[0])
            return jsonify({'error': 'Parsing failed: MCQ format not recognized.'}), 500

        return jsonify({
            'success': True,
            'topic': topic,
            'count': len(structured),
            'test': structured,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.get_json()
        topic = data.get('topic') or data.get('subcategory')
        if topic:
            topic = topic.replace("-", " ").title()
        else:
            return jsonify({'error': 'Topic is missing'}), 400

        count = data.get('count', 1)
        if topic not in topic_prompts:
            return jsonify({'error': f"Invalid topic. Available: {list(topic_prompts.keys())}"}), 400
        if not isinstance(count, int) or not (1 <= count <= 5):
            return jsonify({'error': 'Count must be an integer between 1 and 5'}), 400

        sections = generate_study_material(topic, count)
        if not sections:
            return jsonify({'error': 'Failed to generate content'}), 500

        pdf_buffer = create_pdf(sections, f"{topic} Practice Set")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_buffer.getvalue())
            tmp_path = tmp.name

        filename = f"{topic.lower().replace(' ', '_')}_clat_practice.pdf"
        return send_file(tmp_path, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route("/topics", methods=['GET'])
def get_topics():
    return jsonify({
        'topics': list(topic_prompts.keys()),
        'count': len(topic_prompts),
        'descriptions': {
            'Critical Reasoning': 'Logical argument analysis',
            'General Knowledge': 'Current affairs & static',
            'Legal Reasoning': 'Legal principles and reasoning',
            'Mathematics': 'Quantitative aptitude',
            'Reading Comprehension': 'Abstract and inference-based RC'
        }
    })

@app.route("/health", methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'groq_configured': bool(GROQ_API_KEY),
        'topics_available': len(topic_prompts),
        'timestamp': datetime.now().isoformat()
    })

@app.route("/api/generate-practice", methods=["POST"])
def generate_practice():
    try:
        data = request.get_json()
        section = data.get("section")
        subcategory = data.get("subcategory")
        passages = data.get("passages", 1)

        if not section or not subcategory:
            return jsonify({"error": "Section and subcategory are required"}), 400

        topic_name = subcategory.replace("-", " ").title()
        if topic_name not in topic_prompts:
            return jsonify({"error": f"Unsupported topic: {topic_name}"}), 400

        generated = generate_study_material(topic_name, passages)
        if not generated:
            return jsonify({"error": "Content generation failed"}), 500

        all_questions = []
        for p_index, raw in enumerate(generated):
            questions = parse_mcqs(raw)
            for q_index, q in enumerate(questions):
                all_questions.append({
                    "passageIndex": p_index,
                    "id": f"{p_index}-{q_index}",
                    "passage": q["passage"],
                    "question": q["question"],
                    "options": q["options"],
                    "correct": q["correct"],
                    "explanation": q["explanation"]
                })

        return jsonify({
            "success": True,
            "questions": all_questions,
            "total": len(all_questions)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Server error", "details": str(e)}), 500

# ==============================
# Run Server
# ==============================

if __name__ == "__main__":
    print("=" * 70)
    print("✅ CLAT Sectional Generator API Started at http://127.0.0.1:5000")
    print("=" * 70)
    app.run(debug=True, port=5000)
