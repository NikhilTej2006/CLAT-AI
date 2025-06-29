from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import traceback
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json # Already in main-app, kept for consistency
import os
import traceback
import re
from datetime import datetime
from fpdf import FPDF # From app.py
from io import BytesIO # From app.py
import tempfile # From app.py
import fitz # From main-app.py, for PDF parsing

app = Flask(__name__)
CORS(app)

# =============================================================================
# Groq API Configuration - MERGED
# =============================================================================
# Using the API key from the second app.py as it seems to be the most recent.
# You might want to consolidate this or use environment variables.
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct" # From app.py, default model

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# =============================================================================
# SYSTEM PROMPTS FOR DIFFERENT SERVICES - MERGED
# =============================================================================

# GK Research Engine System Prompt (from main-app.py)
GK_SYSTEM_PROMPT = """GK & CA (GENERAL KNOWLEDGE & CURRENT AFFAIRS)

You are a *General Knowledge passage generator* trained on the *CLAT (Common Law Admission Test)* pattern. Your task is to generate *one full-length GK passage, followed by **five extremely challenging and purely fact-based MCQs, and a **clean answer key* — modeled on CLAT 2020–2024 pattern.

---

### 📘 PASSAGE FORMAT:

*Passage Numbering (MANDATORY):*
Start the passage *inline, with a single numeral on the **same line* as the passage begins.
✅ Correct: 1 After weeks of back-and-forth negotiations, the India–EU Free Trade Agreement remains stalled due to...
❌ Incorrect: Numbering on a separate line or paragraph.

*Length Requirement (NON-NEGOTIABLE):*
The passage must be *minimum 600 words* and can go up to *750 words* if needed.

*Tone & Style:*

* Explanatory and contextual, not opinionated
* Formal journalistic tone (like Indian Express 'Explained' or The Hindu Insight)
* Paragraphs must build *relevant background* and give *conceptual setup*

*CRUCIAL RULE – CONTEXT-ONLY, NEVER DISCLOSE ANSWERS:*

> The passage must *never directly state* the answers to the MCQs. It must only provide enough *background context* so that a student who already knows the facts (or has prepared GK properly) can connect the dots.

Examples:

* If asking a question on "Which organisation published the Global Gender Gap Index?", the passage may discuss gender parity in India — *but must not name the WEF*.
* If asking about the recent *Chief Guest at Republic Day, the passage can talk about India's global diplomacy — **but must not mention the name*.

---

### ❗ QUESTION GENERATION (1.1 to 1.5):

* Create *exactly 5 MCQs* per passage
* Number them inline as 1.1, 1.2, ..., 1.5
* Each stem must be:

    * *Factual*
    * *Verifiable independently*
    * *Not answerable directly from the passage*

*Question Types Allowed:*

* "Which of the following statements is true / not true?"
* "Match the following" (Pair type)
* "Arrange chronologically"
* "Identify the correct authority/author/organisation behind an action"
* "What is the correct fact among these options?"

*Difficulty Benchmark (MANDATORY):*

* All questions must be *difficult* — test memory, prep depth, or confusion traps
* At least *3 questions* must require elimination of very close options
* Avoid guessable or general awareness trivia

---

### 🎯 OPTION STRUCTURE:

* 4 options per question: *(A), (B), (C), (D)*
* Only one must be correct
* Distractors must:

    * Sound reasonable
    * Include *topical but incorrect* choices (e.g., similar agencies, similar events)
    * Be hard to eliminate without actual GK knowledge

---

### ✅ ANSWER KEY FORMAT:

At the end of all 5 questions, provide a *clean answer key*:

Example:
*1.1 – (C)*
*1.2 – (B)*
*1.3 – (A)*
*1.4 – (D)*
*1.5 – (C)*

> No explanations unless explicitly asked.

---

### 🔚 STRUCTURE SUMMARY:

* *Passage:* Numbered inline, 600–750 words, strictly *background/contextual only*
* *Questions:* 5 memory/GK-based MCQs, not directly answerable from passage
* *Options:* Close, confusing, must require real GK knowledge
* *Answer Key:* Clean, numbered, no reasoning"""

# Lexa Chatbot System Prompt (from main-app.py)
LEXA_SYSTEM_PROMPT = """
You are Lexa, an AI assistant specialized in CLAT (Common Law Admission Test) preparation. You are knowledgeable about:

1. Constitutional Law - Articles, Amendments, Landmark Cases
2. Legal Reasoning - Principles, Maxims, Case Studies
3. Current Affairs - Recent legal developments, judgments
4. English Language - Reading comprehension, grammar
5. Logical Reasoning - Analytical and critical thinking
6. Quantitative Techniques - Basic mathematics for law

Provide accurate, helpful, and encouraging responses. Keep answers concise but comprehensive. Always relate responses back to CLAT preparation when relevant.
"""

# QT Mentor System Prompt (from main-app.py)
QT_SYSTEM_PROMPT = """
You are a Quantitative Aptitude generator trained on the CLAT (Common Law Admission Test) pattern. Your task is to generate one complete Quantitative Aptitude passage, followed by exactly 6 multiple-choice questions, and a fully explained answer key.
donot say this is the generated or any bs like that
FORMAT REQUIREMENTS:
- Start passage with: "1 In recent years..." (number inline)
- Write 7-10 neutral tone sentences for the passage with realistic numerical data
- NO title for the passage

QUESTIONS FORMAT:
- Label questions as: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
- Each question must have exactly 4 options: (A), (B), (C), (D)
- Only one correct answer per question
- Questions should test analytical and calculation skills

ANSWER KEY FORMAT:
- Provide detailed step-by-step working
- Format: "1.1 – (B) [detailed explanation with calculations, the explanation should be as if youre explaining to a 5 year old, and it should be lengthy, simple to understand ]"
- Include mathematical calculations where applicable
- Be thorough in explanations, almost like explainaing to a child, and be lengthy, i need 100 word explanations.

EXAMPLE FORMAT:
1 In recent years, the XYZ company has seen significant growth...

1.1 What is the percentage increase in sales from 2020 to 2023?
(A) 25%
(B) 30%
(C) 35%
(D) 40%

1.2 If the company's profit margin is 15%, what was the profit in 2023?
(A) ₹150,000
(B) ₹200,000
(C) ₹250,000
(D) ₹300,000

[Continue for all 6 questions]

Answer Key:
1.1 – (B) To find the percentage increase: (New Value - Old Value)/Old Value × 100 = (1300-1000)/1000 × 100 = 30%

1.2 – (C) Profit = Revenue × Profit Margin = ₹1,666,667 × 15% = ₹250,000

[Continue for all answers]

IMPORTANT: Output must be directly readable text, NOT code. Generate content that matches CLAT examination standards with proper numerical data and realistic scenarios.
"""

# Dynamic Topic Prompts for Generate Test / Practice (from app.py)
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


# =============================================================================
# TOPIC CONTEXTS & MAPPINGS - MERGED
# =============================================================================

# GK Research Engine Topics (from main-app.py)
TOPIC_CONTEXTS = {
    "Indian Politics": "Focus on recent political developments, electoral reforms, constitutional amendments, governance issues, and policy implementations in India.",
    "Economics": "Cover economic policies, budget allocations, GDP trends, inflation, monetary policy, trade relations, and economic reforms in India.",
    "International Relations": "Include diplomatic relations, international treaties, global organizations, bilateral agreements, and India's foreign policy initiatives.",
    "Environment": "Address climate change policies, environmental protection laws, renewable energy initiatives, conservation efforts, and sustainable development goals.",
    "Science & Technology": "Cover technological innovations, space missions, digital initiatives, research developments, and scientific achievements in India.",
    "Social Issues": "Focus on education policies, healthcare initiatives, social welfare schemes, gender equality, and social justice measures.",
    "Legal Affairs": "Include Supreme Court judgments, legal reforms, constitutional matters, judicial appointments, and landmark legal decisions.",
    "History & Culture": "Cover historical events, cultural heritage, archaeological discoveries, traditional practices, and their contemporary relevance."
}

# QT Mentor Topic Mapping (from main-app.py)
QT_TOPIC_MAPPING = {
    "tables": "data interpretation using tables with numerical data including sales figures, population data, or financial statements",
    "bar-charts": "data interpretation using bar charts showing comparative analysis of multiple categories over time",
    "line-graphs": "data interpretation using line graphs showing trend analysis over multiple years",
    "pie-charts": "data interpretation using pie charts showing percentage distribution of categories",
    "percentages": "percentage calculations including profit/loss, percentage changes, and percentage-based word problems",
    "ratios": "ratios, proportions, and comparative relationships with real-world applications",
    "averages": "mean, median, mode, and weighted averages with practical scenarios",
    "profit-loss": "profit and loss calculations including cost price, selling price, discount, and markup problems",
    "compound-interest": "compound interest, simple interest, and banking calculations with time-based scenarios",
    "time-work": "time and work problems including work rates, efficiency, and collaborative work scenarios",
    "speed-distance": "speed, distance, time problems including relative motion and average speed calculations"
}

# =============================================================================
# UTILITY FUNCTIONS - MERGED AND ADAPTED
# =============================================================================

def call_groq_api(messages, temperature=0.7, max_tokens=4000):
    """Generic function to call Groq API"""
    payload = {
        "model": MODEL, # Using the MODEL variable defined globally
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        return data['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        print(f"[Groq API Error] {e}") # Added more specific error for debugging
        return None
    except KeyError as e:
        print(f"Error parsing Groq API response (KeyError): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in call_groq_api: {e}")
        return None

def validate_qt_content(content):
    """Basic validation to ensure QT content quality (from main-app.py)"""
    try:
        # Check if content has minimum length
        if len(content) < 500:
            return False

        # The commented-out regex checks from main-app.py were not fully implemented.
        # Keeping them commented to avoid breaking existing logic, but noting they aren't active.
        # # Check for presence of questions (1.1, 1.2, etc.)
        # question_pattern = r'\d+\.\d+'
        # questions = re.findall(question_pattern, content)
        # if len(questions) < 6:
        #    return False

        # # Check for presence of options
        # option_pattern = r'$$[A-D]$$' # This regex seems incorrect for single letters
        # options = re.findall(option_pattern, content)
        # if len(options) < 24: # 6 questions × 4 options each
        #    return False

        # # Check for answer key
        # if 'Answer Key' not in content:
        #    return False

        return True
    except:
        return False

def generate_study_material(topic, count):
    """Generates study material based on a topic (from app.py, adapted for model)"""
    all_sections = []
    # Using the global MODEL variable for consistency
    system_prompt = "You are an expert CLAT study material generator. Ensure all outputs strictly adhere to the specified format."

    for i in range(count):
        print(f"📝 Generating section {i+1}/{count} for {topic}...")
        prompt = topic_prompts.get(topic, f"Generate a CLAT-level {topic} test with passage, questions, and answer key following the format described.")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        result = call_groq_api(messages)
        if result:
            all_sections.append(f"Topic: {topic}\n\n{result.strip()}")
        else:
            print(f"❌ Failed to generate section {i+1} for {topic}")
    return all_sections

def parse_mcqs(raw_text):
    """Parses MCQs from raw text (from app.py)"""
    parts = re.split(r'\*\*MCQs\*\*', raw_text)
    if len(parts) < 2:
        # If no **MCQs** heading, try to extract based on question numbering
        question_pattern = r'(\d+\.\s*(.+?)\n\(A\).+?Answer:\s*\(([A-D])\)\s*\nExplanation:\s*(.+?)(?=\n\d+\.|\Z))'
        matches = re.findall(question_pattern, raw_text, re.DOTALL)
        if not matches:
            print("[DEBUG] No **MCQs** heading and no clear question patterns found.")
            return []

        structured_questions = []
        for match in matches:
            try:
                full_block, question_text, correct_letter, explanation = match
                question_number_match = re.match(r'(\d+)\.', full_block)
                if not question_number_match:
                    continue # Skip if no question number found at start

                idx = int(question_number_match.group(1))
                question = re.sub(r'^\d+\.\s*', '', question_text).strip()

                options_match = re.findall(r'\(([A-D])\)\s*(.+)', full_block)
                options = [opt[1].strip() for opt in options_match]

                correct_index = ord(correct_letter) - ord('A')

                # Extract passage (everything before the first question)
                passage_start_match = re.search(r'^\d+\s', raw_text, re.MULTILINE)
                passage = raw_text[:passage_start_match.start()].strip() if passage_start_match else ""

                structured_questions.append({
                    "id": idx,
                    "passage": passage, # This will be the same passage for all questions in this set
                    "question": question,
                    "options": options,
                    "correct": correct_index,
                    "explanation": explanation
                })
            except Exception as e:
                print(f"[ERROR PARSING ADAPTED Q]: {e}")
                continue
        return structured_questions


    passage = parts[0].strip()
    mcqs_text = parts[1].strip()

    # Updated regex to correctly split question blocks
    question_blocks = re.findall(r'(\d+\..*?Answer:\s*\([A-D]\)\s*\nExplanation:.*?)(?=\n\d+\.|\Z)', mcqs_text, re.DOTALL)
    structured_questions = []

    for idx, block in enumerate(question_blocks, start=1):
        try:
            q_match = re.search(r'\d+\.\s*(.+?)\n\(A\)', block, re.DOTALL)
            question = q_match.group(1).strip() if q_match else "Unknown question"

            options = []
            for opt_char in ['A', 'B', 'C', 'D']:
                opt_match = re.search(rf'\({opt_char}\)\s*(.+)', block)
                options.append(opt_match.group(1).strip() if opt_match else f"Option {opt_char} not found")

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
            print(f"[ERROR PARSING Q{idx} from standard format]: {e}")
            continue

    return structured_questions


def create_pdf(contents, title):
    """Creates a PDF from content (from app.py)"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    try:
        # Ensure font path is correctly handled or use a widely available font
        font_path = "DejaVuSans.ttf" # This font might not be available by default
        if os.path.exists(font_path):
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", size=12)
        else:
            # Fallback to Arial, which should be available
            pdf.set_font("Arial", size=12)
            print("Warning: DejaVuSans.ttf not found. Using Arial.")
    except Exception as e:
        print(f"Error loading font, falling back to Arial: {e}")
        pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10) # Add a bit more space after title

    for section in contents:
        try:
            # Attempt to encode/decode for special characters, falling back to basic ASCII if needed
            clean_section = section.encode('latin1', 'replace').decode('latin1')
        except:
            clean_section = section
        pdf.multi_cell(0, 7, clean_section) # Reduced line height for better spacing
        pdf.ln(5) # Smaller line break between sections
    return BytesIO(pdf.output(dest='S').encode('latin1'))


# =============================================================================
# MAIN ROUTES - MERGED AND RE-ORGANIZED
# =============================================================================

@app.route("/", methods=["GET"])
def home():
    """Main home endpoint (from main-app.py)"""
    return jsonify({
        "message": "CLAT Unified API - All Services Running",
        "version": "1.0.0",
        "services": {
            "gk_research": "Generate GK passages and MCQs",
            "lexa_chatbot": "CLAT-focused AI assistant",
            "qt_mentor": "Quantitative Aptitude question generator",
            "test_generator": "Generate sectional tests and practice questions",
            "pdf_download": "Download generated tests as PDF"
        },
        "endpoints": {
            "/": "GET - Main home endpoint",
            "/health": "GET - Comprehensive health check for all services",
            # GK Research
            "/gk/generate": "POST - Generate GK passages and MCQs",
            "/gk/topics": "GET - Get available GK topics",
            "/gk/assistant": "POST - Chat with GK study assistant",
            "/gk/upload-pdf": "POST - Generate GK from uploaded PDF",
            # Lexa Chatbot
            "/lexa/chat": "POST - Chat with Lexa assistant",
            # QT Mentor
            "/qt/generate-question": "POST - Generate QT questions",
            "/qt/test": "GET - Test QT service connection",
            # Test & Practice Generation (from app.py)
            "/generate-test": "POST - Generate a single test passage with MCQs",
            "/download-pdf": "POST - Generate and download a test as PDF",
            "/topics": "GET - Get available test generation topics",
            "/api/generate-practice": "POST - Generate practice questions for online consumption"
        },
        "status": "All services operational"
    })

# ---
## GK Research Engine Routes
# ---

@app.route('/gk/generate', methods=['POST'])
def gk_generate_response():
    """Generate GK passage based on user input (from main-app.py)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        topic = data.get('topic', None)

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        print(f"GK Request - Message: {user_message[:100]}..., Topic: {topic}")

        # Enhance the user message with topic context if available
        enhanced_message = user_message
        if topic and topic in TOPIC_CONTEXTS:
            enhanced_message = f"{user_message}\n\nTopic Context: {TOPIC_CONTEXTS[topic]}\n\nPlease generate a passage specifically focused on {topic} with current and relevant examples."

        messages = [
            {"role": "system", "content": GK_SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_message}
        ]

        response = call_groq_api(messages)

        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq API'}), 500

        print(f"GK Generated response length: {len(response)} characters")

        return jsonify({
            'response': response,
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'service': 'gk_research'
        })

    except Exception as e:
        print(f"Error in gk_generate_response: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/gk/assistant', methods=['POST'])
def gk_study_assistant():
    """GK Study Assistant (from main-app.py)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message is empty'}), 400

        print(f"Study Assistant Request: {user_message[:100]}...")

        assistant_prompt = """You are a CLAT study assistant.
Your job is to:
- Explain topics in simple, structured, academic style
- Summarize passages or documents clearly
- Help students understand, take notes, or break down complex issues
Do NOT generate questions unless explicitly asked.
"""

        messages = [
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": user_message}
        ]

        response = call_groq_api(messages)
        if response is None:
            return jsonify({'error': 'Failed to generate assistant response'}), 500

        return jsonify({
            'response': response,
            'service': 'gk_assistant',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Study assistant error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/gk/topics', methods=['GET'])
def gk_get_topics():
    """Get available GK topics with their contexts (from main-app.py)"""
    return jsonify({
        'topics': list(TOPIC_CONTEXTS.keys()),
        'contexts': TOPIC_CONTEXTS,
        'service': 'gk_research'
    })

@app.route('/gk/upload-pdf', methods=['POST'])
def gk_upload_pdf():
    """Generate GK passage and MCQs from uploaded PDF (from main-app.py)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # Extract text from PDF using PyMuPDF
        doc = fitz.open(stream=file.read(), filetype='pdf')
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close() # Close the document after reading

        if not text.strip():
            return jsonify({'error': 'No text found in PDF'}), 400

        # Create prompt with extracted text
        messages = [
            {"role": "system", "content": GK_SYSTEM_PROMPT},
            {"role": "user", "content": f"Based on the following document, generate a CLAT-style GK passage and 5 MCQs:\n\n{text}"}
        ]

        # Send to Groq API
        response = call_groq_api(messages)
        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq'}), 500

        return jsonify({
            'response': response,
            'source': 'uploaded_pdf',
            'timestamp': datetime.now().isoformat(),
            'service': 'gk_research'
        })

    except Exception as e:
        print(f"PDF upload error: {e}")
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({'error': 'Server error processing PDF', 'details': str(e)}), 500


# ---
## Lexa Chatbot Routes
# ---

@app.route("/lexa/chat", methods=["POST"])
def lexa_chat():
    """Chat with Lexa CLAT assistant (from main-app.py)"""
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400

        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        print(f"Lexa Chat - Message: {user_message[:100]}...")

        messages = [
            {"role": "system", "content": LEXA_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        response = call_groq_api(messages, temperature=0.7, max_tokens=1024)

        if response is None:
            return jsonify({"error": "Failed to get response from Lexa"}), 500

        return jsonify({
            "response": response,
            "status": "success",
            "service": "lexa_chatbot",
            "timestamp": datetime.now().isoformat()
        })

    except requests.exceptions.Timeout:
        print("Lexa request timeout")
        return jsonify({"error": "Request timeout"}), 504

    except Exception as e:
        print(f"Lexa Server Exception: {str(e)}")
        traceback.print_exc() # Print full traceback
        return jsonify({"error": "Server Exception", "message": str(e)}), 500

# ---
## QT Mentor Routes
# ---

@app.route("/qt/test", methods=["GET"])
def qt_test_connection():
    """Test QT Mentor connection (from main-app.py)"""
    return jsonify({
        "status": "success",
        "message": "QT Mentor API connection successful",
        "service": "qt_mentor",
        "available_topics": list(QT_TOPIC_MAPPING.keys())
    })

@app.route("/qt/generate-question", methods=["POST"])
def qt_generate_question():
    """Generate QT questions based on topic (from main-app.py)"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        topic = data.get("topic", "percentages")
        print(f"QT Request for topic: {topic}")

        detailed_topic = QT_TOPIC_MAPPING.get(topic, topic)
        print(f"QT Mapped to detailed topic: {detailed_topic}")

        # Enhanced user prompt for better quality
        user_prompt = f"""Generate a CLAT-style Quantitative Aptitude passage and exactly 6 questions on the topic: '{detailed_topic}'.

Requirements:
1. Create a realistic business/economic scenario with specific numerical data
2. Passage should be 7-10 sentences with concrete numbers
3. Questions should progressively increase in difficulty
4. Each question must test different aspects of the topic
5. Ensure calculations are accurate and explanations are detailed
6. Use realistic Indian context (₹ currency, Indian companies/cities)

Topic focus: {detailed_topic}

Please follow the exact format specified in the system prompt."""

        messages = [
            {"role": "system", "content": QT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        print("Making QT request to Groq API...")

        response = call_groq_api(messages, temperature=0.7, max_tokens=4000)

        if response is None:
            return jsonify({
                "success": False,
                "error": "Failed to generate QT content",
                "service": "qt_mentor"
            }), 500

        print(f"QT Generated content length: {len(response)}")

        # Basic validation of generated content
        if not validate_qt_content(response):
            print("QT Content validation failed")
            return jsonify({
                "success": False,
                "error": "Generated content doesn't meet quality standards",
                "details": "Please try generating again",
                "service": "qt_mentor"
            }), 400

        return jsonify({
            "success": True,
            "rawOutput": response,
            "topic": topic,
            "contentLength": len(response),
            "service": "qt_mentor",
            "timestamp": datetime.now().isoformat()
        })

    except requests.exceptions.Timeout:
        print("QT Request timeout occurred")
        return jsonify({
            "success": False,
            "error": "Request timeout",
            "message": "API request took too long. Please try again.",
            "service": "qt_mentor"
        }), 500

    except Exception as e:
        print(f"QT Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Server Exception",
            "message": str(e),
            "service": "qt_mentor"
        }), 500

# ---
## Test Generation & Practice Routes
# ---

@app.route("/generate-test", methods=['POST'])
def generate_content():
    """Generate a test passage with MCQs for a given topic (from app.py)"""
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

        structured = parse_mcqs(sections[0]) # Only parsing the first section for this endpoint
        if not structured:
            print("\n[DEBUG] Raw output for parsing failure in generate_content:\n", sections[0])
            return jsonify({'error': 'Parsing failed: MCQ format not recognized. Check raw output for format issues.'}), 500

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
    """Generate and download a test as PDF (from app.py)"""
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
            return jsonify({'error': 'Failed to generate content for PDF'}), 500

        pdf_buffer = create_pdf(sections, f"{topic} Practice Set")
        # Using a temporary file to send the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_buffer.getvalue())
            tmp_path = tmp.name

        filename = f"{topic.lower().replace(' ', '_')}_clat_practice.pdf"
        # The 'after_request' tear down is not explicitly defined in your combined code,
        # so relying on OS/server to clean up temp file after response if needed.
        return send_file(tmp_path, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal server error during PDF generation', 'details': str(e)}), 500

@app.route("/topics", methods=['GET'])
def get_topics():
    """Get available test generation topics and descriptions (from app.py)"""
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

@app.route("/api/generate-practice", methods=["POST"])
def generate_practice():
    """Generate practice questions for online consumption (from app.py)"""
    try:
        data = request.get_json()
        section = data.get("section") # This 'section' isn't directly used in current logic but might be for categorization
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

# ---
## Health Check Routes
# ---

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check for all services (from main-app.py, combined with app.py's health)"""
    return jsonify({
        'status': 'healthy',
        'message': 'All CLAT services are running',
        'services': {
            'gk_research': 'operational',
            'lexa_chatbot': 'operational',
            'qt_mentor': 'operational',
            'test_generator': 'operational', # New service status
            'pdf_download': 'operational' # New service status
        },
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat(),
        'available_topics': {
            'gk_topics': list(TOPIC_CONTEXTS.keys()),
            'qt_topics': list(QT_TOPIC_MAPPING.keys()),
            'general_test_topics': list(topic_prompts.keys()) # Added topics from app.py
        }
    })

# Legacy health endpoints for backward compatibility (from main-app.py)
@app.route('/gk/health', methods=['GET'])
def gk_health_check():
    """GK Research Engine health check"""
    return jsonify({
        'status': 'healthy',
        'message': 'GK Research Engine API is running',
        'service': 'gk_research',
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/lexa/health', methods=['GET'])
def lexa_health_check():
    """Lexa Chatbot health check"""
    return jsonify({
        "status": "healthy",
        "message": "CLAT Chatbot API is running",
        "service": "lexa_chatbot",
        "timestamp": datetime.now().isoformat()
    })

# (The /health endpoint from app.py is effectively merged into the comprehensive health_check above.
# I'll keep the name health_check from main-app.py as it's more comprehensive and will be the main one.)


# =============================================================================
# ERROR HANDLERS - MERGED
# =============================================================================

@app.errorhandler(404)
def not_found(error): # Renamed 'e' to 'error' for consistency with main-app.py's handler
    """Custom 404 handler (merged from both files)"""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "main": "/",
            "gk_research": ["/gk/generate", "/gk/topics", "/gk/assistant", "/gk/upload-pdf", "/gk/health"],
            "lexa_chatbot": ["/lexa/chat", "/lexa/health"],
            "qt_mentor": ["/qt/generate-question", "/qt/test"],
            "test_generation": ["/generate-test", "/download-pdf", "/topics", "/api/generate-practice"], # New endpoints
            "health": "/health"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error): # Renamed 'e' to 'error' for consistency with main-app.py's handler
    """Custom 500 handler (merged from both files)"""
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on the server",
        "details": str(error) if app.debug else "Enable debug mode for more details" # Added details
    }), 500

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Check if API key is set
    if not GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set!")

    print("=" * 80)
    print("🚀 Starting CLAT Unified API Server")
    print("=" * 80)
    print(f"📍 Server URL: http://127.0.0.1:5000")
    print(f"🔗 Main endpoint: http://127.0.0.1:5000/")
    print(f"📚 GK Research: http://127.0.0.1:5000/gk/generate")
    print(f"🤖 Lexa Chatbot: http://127.0.0.1:5000/lexa/chat")
    print(f"🔢 QT Mentor: http://127.0.0.1:5000/qt/generate-question")
    print(f"📝 Test Generator: http://127.0.0.1:5000/generate-test")
    print(f"⬇️ PDF Download: http://127.0.0.1:5000/download-pdf")
    print(f"💡 Topics List: http://127.0.0.1:5000/topics")
    print(f"🌐 Online Practice: http://127.0.0.1:5000/api/generate-practice")
    print(f"❤️ Health Check: http://127.0.0.1:5000/health")
    print("=" * 80)
    print(f"Groq API configured: {'Yes' if GROQ_API_KEY else 'No'}")
    print(f"GK Topics available: {len(TOPIC_CONTEXTS)}")
    print(f"QT Topics available: {len(QT_TOPIC_MAPPING)}")
    print(f"General Test Topics available: {len(topic_prompts)}")
    print("=" * 80)

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

# Groq API configuration
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# =============================================================================
# SYSTEM PROMPTS FOR DIFFERENT SERVICES
# =============================================================================

# GK Research Engine System Prompt
GK_SYSTEM_PROMPT = """GK & CA (GENERAL KNOWLEDGE & CURRENT AFFAIRS)

You are a *General Knowledge passage generator* trained on the *CLAT (Common Law Admission Test)* pattern. Your task is to generate *one full-length GK passage, followed by **five extremely challenging and purely fact-based MCQs, and a **clean answer key* — modeled on CLAT 2020–2024 pattern.

---

### 📘 PASSAGE FORMAT:

*Passage Numbering (MANDATORY):*
Start the passage *inline, with a single numeral on the **same line* as the passage begins.
✅ Correct: 1 After weeks of back-and-forth negotiations, the India–EU Free Trade Agreement remains stalled due to...
❌ Incorrect: Numbering on a separate line or paragraph.

*Length Requirement (NON-NEGOTIABLE):*
The passage must be *minimum 600 words* and can go up to *750 words* if needed.

*Tone & Style:*

* Explanatory and contextual, not opinionated
* Formal journalistic tone (like Indian Express 'Explained' or The Hindu Insight)
* Paragraphs must build *relevant background* and give *conceptual setup*

*CRUCIAL RULE – CONTEXT-ONLY, NEVER DISCLOSE ANSWERS:*

> The passage must *never directly state* the answers to the MCQs. It must only provide enough *background context* so that a student who already knows the facts (or has prepared GK properly) can connect the dots.

Examples:

* If asking a question on "Which organisation published the Global Gender Gap Index?", the passage may discuss gender parity in India — *but must not name the WEF*.
* If asking about the recent *Chief Guest at Republic Day, the passage can talk about India's global diplomacy — **but must not mention the name*.

---

### ❗ QUESTION GENERATION (1.1 to 1.5):

* Create *exactly 5 MCQs* per passage
* Number them inline as 1.1, 1.2, ..., 1.5
* Each stem must be:

  * *Factual*
  * *Verifiable independently*
  * *Not answerable directly from the passage*

*Question Types Allowed:*

* "Which of the following statements is true / not true?"
* "Match the following" (Pair type)
* "Arrange chronologically"
* "Identify the correct authority/author/organisation behind an action"
* "What is the correct fact among these options?"

*Difficulty Benchmark (MANDATORY):*

* All questions must be *difficult* — test memory, prep depth, or confusion traps
* At least *3 questions* must require elimination of very close options
* Avoid guessable or general awareness trivia

---

### 🎯 OPTION STRUCTURE:

* 4 options per question: *(A), (B), (C), (D)*
* Only one must be correct
* Distractors must:

  * Sound reasonable
  * Include *topical but incorrect* choices (e.g., similar agencies, similar events)
  * Be hard to eliminate without actual GK knowledge

---

### ✅ ANSWER KEY FORMAT:

At the end of all 5 questions, provide a *clean answer key*:

Example:
*1.1 – (C)*
*1.2 – (B)*
*1.3 – (A)*
*1.4 – (D)*
*1.5 – (C)*

> No explanations unless explicitly asked.

---

### 🔚 STRUCTURE SUMMARY:

* *Passage:* Numbered inline, 600–750 words, strictly *background/contextual only*
* *Questions:* 5 memory/GK-based MCQs, not directly answerable from passage
* *Options:* Close, confusing, must require real GK knowledge
* *Answer Key:* Clean, numbered, no reasoning"""

# Lexa Chatbot System Prompt
LEXA_SYSTEM_PROMPT = """
You are Lexa, an AI assistant specialized in CLAT (Common Law Admission Test) preparation. You are knowledgeable about:

1. Constitutional Law - Articles, Amendments, Landmark Cases
2. Legal Reasoning - Principles, Maxims, Case Studies  
3. Current Affairs - Recent legal developments, judgments
4. English Language - Reading comprehension, grammar
5. Logical Reasoning - Analytical and critical thinking
6. Quantitative Techniques - Basic mathematics for law

Provide accurate, helpful, and encouraging responses. Keep answers concise but comprehensive. Always relate responses back to CLAT preparation when relevant.
"""

# QT Mentor System Prompt
QT_SYSTEM_PROMPT = """
You are a Quantitative Aptitude generator trained on the CLAT (Common Law Admission Test) pattern. Your task is to generate one complete Quantitative Aptitude passage, followed by exactly 6 multiple-choice questions, and a fully explained answer key.
donot say this is the generated or any bs like that
FORMAT REQUIREMENTS:
- Start passage with: "1 In recent years..." (number inline)
- Write 7-10 neutral tone sentences for the passage with realistic numerical data
- NO title for the passage

QUESTIONS FORMAT:
- Label questions as: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
- Each question must have exactly 4 options: (A), (B), (C), (D)
- Only one correct answer per question
- Questions should test analytical and calculation skills

ANSWER KEY FORMAT:
- Provide detailed step-by-step working
- Format: "1.1 – (B) [detailed explanation with calculations, the explanation should be as if youre explaining to a 5 year old, and it should be lengthy, simple to understand ]"
- Include mathematical calculations where applicable
- Be thorough in explanations, almost like explainaing to a child, and be lengthy, i need 100 word explanations.

EXAMPLE FORMAT:
1 In recent years, the XYZ company has seen significant growth...

1.1 What is the percentage increase in sales from 2020 to 2023?
(A) 25%
(B) 30%
(C) 35%
(D) 40%

1.2 If the company's profit margin is 15%, what was the profit in 2023?
(A) ₹150,000
(B) ₹200,000
(C) ₹250,000
(D) ₹300,000

[Continue for all 6 questions]

Answer Key:
1.1 – (B) To find the percentage increase: (New Value - Old Value)/Old Value × 100 = (1300-1000)/1000 × 100 = 30%

1.2 – (C) Profit = Revenue × Profit Margin = ₹1,666,667 × 15% = ₹250,000

[Continue for all answers]

IMPORTANT: Output must be directly readable text, NOT code. Generate content that matches CLAT examination standards with proper numerical data and realistic scenarios.
"""

# =============================================================================
# TOPIC CONTEXTS FOR GK RESEARCH ENGINE
# =============================================================================

TOPIC_CONTEXTS = {
    "Indian Politics": "Focus on recent political developments, electoral reforms, constitutional amendments, governance issues, and policy implementations in India.",
    "Economics": "Cover economic policies, budget allocations, GDP trends, inflation, monetary policy, trade relations, and economic reforms in India.",
    "International Relations": "Include diplomatic relations, international treaties, global organizations, bilateral agreements, and India's foreign policy initiatives.",
    "Environment": "Address climate change policies, environmental protection laws, renewable energy initiatives, conservation efforts, and sustainable development goals.",
    "Science & Technology": "Cover technological innovations, space missions, digital initiatives, research developments, and scientific achievements in India.",
    "Social Issues": "Focus on education policies, healthcare initiatives, social welfare schemes, gender equality, and social justice measures.",
    "Legal Affairs": "Include Supreme Court judgments, legal reforms, constitutional matters, judicial appointments, and landmark legal decisions.",
    "History & Culture": "Cover historical events, cultural heritage, archaeological discoveries, traditional practices, and their contemporary relevance."
}

# =============================================================================
# QT MENTOR TOPIC MAPPING
# =============================================================================

QT_TOPIC_MAPPING = {
    "tables": "data interpretation using tables with numerical data including sales figures, population data, or financial statements",
    "bar-charts": "data interpretation using bar charts showing comparative analysis of multiple categories over time", 
    "line-graphs": "data interpretation using line graphs showing trend analysis over multiple years",
    "pie-charts": "data interpretation using pie charts showing percentage distribution of categories",
    "percentages": "percentage calculations including profit/loss, percentage changes, and percentage-based word problems",
    "ratios": "ratios, proportions, and comparative relationships with real-world applications",
    "averages": "mean, median, mode, and weighted averages with practical scenarios",
    "profit-loss": "profit and loss calculations including cost price, selling price, discount, and markup problems",
    "compound-interest": "compound interest, simple interest, and banking calculations with time-based scenarios",
    "time-work": "time and work problems including work rates, efficiency, and collaborative work scenarios",
    "speed-distance": "speed, distance, time problems including relative motion and average speed calculations"
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
                                                              
def call_groq_api(messages, temperature=0.7, max_tokens=4000):
    """Generic function to call Groq API"""
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9
    }
                                                              
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Groq API: {e}")
        return None
    except KeyError as e:
        print(f"Error parsing Groq API response: {e}")
        return None

def validate_qt_content(content):
    """Basic validation to ensure QT content quality"""
    try:
        # Check if content has minimum length
        if len(content) < 500:
            return False
            
        # Check for presence of questions (1.1, 1.2, etc.)
        # question_pattern = r'\d+\.\d+'
        # questions = re.findall(question_pattern, content)
        # if len(questions) < 6:
        #     return False
            
        # Check for presence of options
        # option_pattern = r'$$[A-D]$$'
        # options = re.findall(option_pattern, content)
        # if len(options) < 24:  # 6 questions × 4 options each
        #     return False
            
        # Check for answer key
        # if 'Answer Key' not in content:
        #     return False
            
        return True
    except:
        return False

# =============================================================================
# MAIN ROUTES
# =============================================================================

@app.route("/", methods=["GET"])
def home():
    """Main home endpoint"""
    return jsonify({
        "message": "CLAT Unified API - All Services Running",
        "version": "1.0.0",
        "services": {
            "gk_research": "Generate GK passages and MCQs",
            "lexa_chatbot": "CLAT-focused AI assistant",
            "qt_mentor": "Quantitative Aptitude question generator"
        },
        "endpoints": {
            "/gk/generate": "POST - Generate GK passages and MCQs",
            "/gk/topics": "GET - Get available GK topics",
            "/lexa/chat": "POST - Chat with Lexa assistant",
            "/qt/generate-question": "POST - Generate QT questions",
            "/qt/test": "GET - Test QT service",
            "/health": "GET - Health check for all services"
        },
        "status": "All services operational"
    })

# =============================================================================
# GK RESEARCH ENGINE ROUTES
# =============================================================================

@app.route('/gk/generate', methods=['POST'])
def gk_generate_response():
    """Generate GK passage based on user input"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        topic = data.get('topic', None)
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"GK Request - Message: {user_message[:100]}..., Topic: {topic}")
        
        # Enhance the user message with topic context if available
        enhanced_message = user_message
        if topic and topic in TOPIC_CONTEXTS:
            enhanced_message = f"{user_message}\n\nTopic Context: {TOPIC_CONTEXTS[topic]}\n\nPlease generate a passage specifically focused on {topic} with current and relevant examples."
        
        messages = [
            {"role": "system", "content": GK_SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_message}
        ]
        
        response = call_groq_api(messages)
        
        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq API'}), 500
        
        print(f"GK Generated response length: {len(response)} characters")
        
        return jsonify({
            'response': response,
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'service': 'gk_research'
        })
        
    except Exception as e:
        print(f"Error in gk_generate_response: {e}")
        return jsonify({'error': 'Internal server error'}), 500
@app.route('/gk/assistant', methods=['POST'])
def gk_study_assistant():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message is empty'}), 400

        print(f"Study Assistant Request: {user_message[:100]}...")

        assistant_prompt = """You are a CLAT study assistant. 
Your job is to:
- Explain topics in simple, structured, academic style
- Summarize passages or documents clearly
- Help students understand, take notes, or break down complex issues
Do NOT generate questions unless explicitly asked.
"""

        messages = [
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": user_message}
        ]

        response = call_groq_api(messages)
        if response is None:
            return jsonify({'error': 'Failed to generate assistant response'}), 500

        return jsonify({
            'response': response,
            'service': 'gk_assistant',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Study assistant error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/gk/topics', methods=['GET'])
def gk_get_topics():
    """Get available GK topics with their contexts"""
    return jsonify({
        'topics': list(TOPIC_CONTEXTS.keys()),
        'contexts': TOPIC_CONTEXTS,
        'service': 'gk_research'
    })

# =============================================================================
# LEXA CHATBOT ROUTES
# =============================================================================

@app.route("/lexa/chat", methods=["POST"])
def lexa_chat():
    """Chat with Lexa CLAT assistant"""
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
            
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        print(f"Lexa Chat - Message: {user_message[:100]}...")

        messages = [
            {"role": "system", "content": LEXA_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        response = call_groq_api(messages, temperature=0.7, max_tokens=1024)

        if response is None:
            return jsonify({"error": "Failed to get response from Lexa"}), 500

        return jsonify({
            "response": response,
            "status": "success",
            "service": "lexa_chatbot",
            "timestamp": datetime.now().isoformat()
        })
    
    except requests.exceptions.Timeout:
        print("Lexa request timeout")
        return jsonify({"error": "Request timeout"}), 504
    
    except Exception as e:
        print(f"Lexa Server Exception: {str(e)}")
        return jsonify({"error": "Server Exception", "message": str(e)}), 500

# =============================================================================
# QT MENTOR ROUTES
# =============================================================================

@app.route("/qt/test", methods=["GET"])
def qt_test_connection():
    """Test QT Mentor connection"""
    return jsonify({
        "status": "success",
        "message": "QT Mentor API connection successful",
        "service": "qt_mentor",
        "available_topics": list(QT_TOPIC_MAPPING.keys())
    })

@app.route("/qt/generate-question", methods=["POST"])
def qt_generate_question():
    """Generate QT questions based on topic"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        topic = data.get("topic", "percentages")
        print(f"QT Request for topic: {topic}")
        
        detailed_topic = QT_TOPIC_MAPPING.get(topic, topic)
        print(f"QT Mapped to detailed topic: {detailed_topic}")

        # Enhanced user prompt for better quality
        user_prompt = f"""Generate a CLAT-style Quantitative Aptitude passage and exactly 6 questions on the topic: '{detailed_topic}'. 

Requirements:
1. Create a realistic business/economic scenario with specific numerical data
2. Passage should be 7-10 sentences with concrete numbers
3. Questions should progressively increase in difficulty
4. Each question must test different aspects of the topic
5. Ensure calculations are accurate and explanations are detailed
6. Use realistic Indian context (₹ currency, Indian companies/cities)

Topic focus: {detailed_topic}

Please follow the exact format specified in the system prompt."""

        messages = [
            {"role": "system", "content": QT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        print("Making QT request to Groq API...")
        
        response = call_groq_api(messages, temperature=0.7, max_tokens=4000)
        
        if response is None:
            return jsonify({
                "success": False,
                "error": "Failed to generate QT content",
                "service": "qt_mentor"
            }), 500
        
        print(f"QT Generated content length: {len(response)}")
        
        # Basic validation of generated content
        if not validate_qt_content(response):
            print("QT Content validation failed")
            return jsonify({
                "success": False,
                "error": "Generated content doesn't meet quality standards",
                "details": "Please try generating again",
                "service": "qt_mentor"
            }), 400

        return jsonify({
            "success": True,
            "rawOutput": response,
            "topic": topic,
            "contentLength": len(response),
            "service": "qt_mentor",
            "timestamp": datetime.now().isoformat()
        })
    
    except requests.exceptions.Timeout:
        print("QT Request timeout occurred")
        return jsonify({
            "success": False,
            "error": "Request timeout", 
            "message": "API request took too long. Please try again.",
            "service": "qt_mentor"
        }), 500
        
    except Exception as e:
        print(f"QT Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Server Exception", 
            "message": str(e),
            "service": "qt_mentor"
        }), 500

# =============================================================================
# HEALTH CHECK ROUTES
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check for all services"""
    return jsonify({
        'status': 'healthy',
        'message': 'All CLAT services are running',
        'services': {
            'gk_research': 'operational',
            'lexa_chatbot': 'operational', 
            'qt_mentor': 'operational'
        },
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat(),
        'available_topics': {
            'gk_topics': list(TOPIC_CONTEXTS.keys()),
            'qt_topics': list(QT_TOPIC_MAPPING.keys())
        }
    })

# Legacy health endpoints for backward compatibility
@app.route('/gk/health', methods=['GET'])
def gk_health_check():
    """GK Research Engine health check"""
    return jsonify({
        'status': 'healthy', 
        'message': 'GK Research Engine API is running',
        'service': 'gk_research',
        'groq_configured': bool(GROQ_API_KEY),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/lexa/health', methods=['GET'])
def lexa_health_check():
    """Lexa Chatbot health check"""
    return jsonify({
        "status": "healthy", 
        "message": "CLAT Chatbot API is running",
        "service": "lexa_chatbot",
        "timestamp": datetime.now().isoformat()
    })

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "main": "/",
            "gk_research": ["/gk/generate", "/gk/topics", "/gk/health"],
            "lexa_chatbot": ["/lexa/chat", "/lexa/health"],
            "qt_mentor": ["/qt/generate-question", "/qt/test"],
            "health": "/health"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on the server"
    }), 500

import fitz  # <-- Already at top of file? Skip this

@app.route('/gk/upload-pdf', methods=['POST'])
def gk_upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # Extract text from PDF using PyMuPDF
        doc = fitz.open(stream=file.read(), filetype='pdf')
        text = ""
        for page in doc:
            text += page.get_text()

        if not text.strip():
            return jsonify({'error': 'No text found in PDF'}), 400

        # Create prompt with extracted text
        messages = [
            {"role": "system", "content": GK_SYSTEM_PROMPT},
            {"role": "user", "content": f"Based on the following document, generate a CLAT-style GK passage and 5 MCQs:\n\n{text}"}
        ]

        # Send to Groq API
        response = call_groq_api(messages)
        if response is None:
            return jsonify({'error': 'Failed to generate response from Groq'}), 500

        return jsonify({
            'response': response,
            'source': 'uploaded_pdf',
            'timestamp': datetime.now().isoformat(),
            'service': 'gk_research'
        })

    except Exception as e:
        print(f"PDF upload error: {e}")
        return jsonify({'error': 'Server error processing PDF'}), 500


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Check if API key is set
    if not GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set!")
    
    print("=" * 80)
    print("🚀 Starting CLAT Unified API Server")
    print("=" * 80)
    print(f"📍 Server URL: http://127.0.0.1:5000")
    print(f"🔗 Main endpoint: http://127.0.0.1:5000/")
    print(f"📚 GK Research: http://127.0.0.1:5000/gk/generate")
    print(f"🤖 Lexa Chatbot: http://127.0.0.1:5000/lexa/chat")
    print(f"🔢 QT Mentor: http://127.0.0.1:5000/qt/generate-question")
    print(f"❤️  Health Check: http://127.0.0.1:5000/health")
    print("=" * 80)
    print(f"Groq API configured: {'Yes' if GROQ_API_KEY else 'No'}")
    print(f"GK Topics available: {len(TOPIC_CONTEXTS)}")
    print(f"QT Topics available: {len(QT_TOPIC_MAPPING)}")
    print("=" * 80)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
