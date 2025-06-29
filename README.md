# 🧠 Generate Tests & Practice Online

An AI-powered test generation and practice platform that allows users to create customized quizzes using **LLMs via the Ollama API**, and practice them interactively through a clean web interface. Built with **Flask** on the backend, this project provides real-time, intelligent, and engaging assessments — ideal for students, educators, and exam aspirants.

---

## 📚 Overview

Manual test creation can be time-consuming and repetitive. This project solves that problem by integrating **Large Language Models** using the **Ollama API**, enabling dynamic generation of topic-based multiple-choice questions (MCQs). With a user-friendly interface and real-time feedback, users can both generate and practice tests instantly.

---

## 🎯 Key Features

- 🧠 **LLM-Driven Generation** – Generates high-quality questions based on input topics.
- ✍️ **Custom Inputs** – Choose topic, number of questions, and difficulty level.
- ⚙️ **Flask-Powered Backend** – RESTful APIs handle test generation and evaluation.
- 💬 **Practice Mode** – Users can attempt quizzes in-browser with immediate feedback.
- 📈 **Real-Time Feedback** – Scores and answer validations provided instantly.

---

## 🛠️ Tech Stack

- **Frontend**: HTML, CSS, JavaScript  
- **Backend**: Python, Flask  
- **AI Integration**: Ollama API (LLM for question generation)  
- **API Format**: REST (JSON responses)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash[
git clone:(https://github.com/NikhilTej2006/CLAT-AI.git)]

 The app.py file serves as the central Flask backend and is responsible for routing and handling both generate-test.html (test creation) and practice.html (test attempt interface) via defined API endpoints or template rendering.
