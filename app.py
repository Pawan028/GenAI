import urllib.parse
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
import time
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta

# Import tenacity for retry logic
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache

# Global API call counter for monitoring (used in addition to session state)
API_CALLS = 0

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("Missing dependencies! Install plotly using: pip install plotly")
    st.stop()

# Load environment variables
load_dotenv()

# Configure Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-1.5-pro"

# Add API rate limiting management via session state
if "api_call_count" not in st.session_state:
    st.session_state.api_call_count = 0
if "last_reset_time" not in st.session_state:
    st.session_state.last_reset_time = datetime.now()
if "quota_limit" not in st.session_state:
    st.session_state.quota_limit = 60  # Adjust based on your API quota

def check_and_reset_quota():
    """Reset counter every 60 minutes and return True if quota remains."""
    current_time = datetime.now()
    if current_time - st.session_state.last_reset_time > timedelta(minutes=60):
        st.session_state.api_call_count = 0
        st.session_state.last_reset_time = current_time
        return True
    return st.session_state.api_call_count < st.session_state.quota_limit

# 1. Enhanced Gemini API call with retry logic and rate limiting
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_gemini_response(user_input, pdf_content, prompt, temperature=0.7, max_tokens=1000):
    """Get response from Gemini AI with enhanced error handling and retry logic."""
    global API_CALLS
    # Rate limiting: ensure max 50 requests per minute
    time.sleep(1.2)
    
    # Check quota before making API call
    if not check_and_reset_quota():
        remaining_time = 60 - ((datetime.now() - st.session_state.last_reset_time).seconds // 60)
        return f"⚠️ API quota limit reached. Please try again in approximately {remaining_time} minutes."
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [user_input, *pdf_content, prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        # Increment counters if successful
        st.session_state.api_call_count += 1
        API_CALLS += 1
        if API_CALLS > 45:  # If we exceed 45 calls (buffer before 50)
            return "⚠️ Daily limit reached. Service resumes in 24 hours."
        return response.text
    except Exception as e:
        if "quota" in str(e).lower():
            st.session_state.api_call_count = st.session_state.quota_limit  # Mark as quota exhausted
            return "⚠️ Our AI systems are currently at capacity. Please try again in 30 minutes."
        return f"❌ Error: {str(e)}"

# 2. Cache common career advice responses
@lru_cache(maxsize=50)
def get_career_advice(question_type: str, skills: str) -> str:
    """Return common career advice responses from cache."""
    advice_map = {
        "resume_improvement": [
            "Highlight quantifiable achievements in your experience section.",
            "Add a skills matrix matching the job requirements.",
            "Include industry-specific keywords from the job description."
        ],
        "job_search": [
            "Optimize your LinkedIn headline with key skills.",
            "Network with industry professionals on LinkedIn Groups.",
            "Tailor your resume for each application."
        ]
    }
    return random.choice(advice_map.get(question_type, ["Keep improving your skills!"]))

# 3. Enhanced PDF Analysis with Local Processing
def analyze_resume_locally(pdf_parts: list) -> dict:
    """Perform a basic local analysis on the resume content extracted from PDF images."""
    from collections import defaultdict
    analysis = defaultdict(list)
    
    # Concatenate the first 2000 characters from each image's base64 (simulate text extraction)
    # For a real solution, use OCR to extract text.
    text = ""
    for part in pdf_parts:
        text += part.get("data", "")[:2000]
    
    # Simple keyword matching
    skills = ["Python", "Project Management", "Data Analysis", "Machine Learning", "Cloud Computing"]
    for skill in skills:
        if skill.lower() in text.lower():
            analysis["skills"].append(skill)
    
    # Experience detection via simple keyword matching
    experience_keywords = ["experience", "worked", "managed"]
    if any(kw in text.lower() for kw in experience_keywords):
        analysis["suggestions"].append("Consider expanding your experience section with quantifiable achievements.")
        
    return analysis

# Custom CSS for modern UI
st.markdown("""
<style>
    :root {
        --primary: #2A2F4F;
        --secondary: #917FB3;
        --accent: #E5BEEC;
        --background: #1A1A1A;
    }
    .stApp {
        background: var(--background);
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin: 2rem 0;
        animation: fadeIn 1s ease-in;
    }
    .app-name {
        font-size: 2.8rem;
        background: linear-gradient(45deg, #E5BEEC, #917FB3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: 2px;
        text-shadow: 0 0 15px rgba(229, 190, 236, 0.4);
    }
    .upload-section:hover {
        border-color: var(--accent) !important;
        background: rgba(145, 127, 179, 0.1) !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(229, 190, 236, 0.3);
    }
    img {
        width: 80px !important;
        height: 80px !important;
        border: 2px solid var(--accent);
        box-shadow: 0 0 25px rgba(229, 190, 236, 0.3);
        transition: transform 0.3s ease;
    }
    img:hover {
        transform: rotate(15deg) scale(1.1);
    }
    .resume-builder-link {
        display: block;
        text-align: center;
        padding: 12px;
        margin: 1rem 0;
        border-radius: 8px;
        background: linear-gradient(45deg, var(--primary), var(--secondary));
        color: white !important;
        text-decoration: none;
        transition: transform 0.3s ease;
    }
    .resume-builder-link:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(229, 190, 236, 0.25);
    }
    .chat-user, .chat-bot {
        animation: slideIn 0.3s ease-out;
        position: relative;
        padding: 10px 15px;
        margin: 8px 0;
        border-radius: 8px;
    }
    .chat-user {
        background: rgba(42, 47, 79, 0.5);
        border-left: 3px solid var(--accent);
    }
    .chat-bot {
        background: rgba(145, 127, 179, 0.2);
        border-left: 3px solid var(--secondary);
    }
    .learning-milestone {
        background: linear-gradient(45deg, var(--primary), var(--secondary));
        padding: 10px 15px;
        border-radius: 8px;
        margin: 8px 0;
        animation: fadeIn 0.5s ease-in;
    }
    .learning-path-title {
        color: var(--accent);
        font-size: 1.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .skill-gap-card {
        background: rgba(42, 47, 79, 0.5);
        border-left: 4px solid var(--accent);
        padding: 12px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .quota-warning {
        background: linear-gradient(45deg, #FF9966, #FF5E62);
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideIn {
        from { transform: translateX(20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--background);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--secondary);
        border-radius: 4px;
    }
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #444;
        border-radius: 8px;
        background: #2D2D2D;
        margin-bottom: 1rem;
    }
    .chat-user {
        background: rgba(42, 47, 79, 0.5);
        border-left: 3px solid #E5BEEC;
        padding: 8px;
        margin: 8px 0;
        border-radius: 8px;
    }
    .chat-bot {
        background: rgba(145, 127, 179, 0.2);
        border-left: 3px solid #917FB3;
        padding: 8px;
        margin: 8px 0;
        border-radius: 8px;
    }

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="logo-container">
    <div class="app-name">🤖 SmartHire</div>
</div>
<h4 style='text-align: center; color: var(--accent);'>Next-Gen AI Recruitment Assistant</h4>
""", unsafe_allow_html=True)

# Session state initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "responses" not in st.session_state:
    st.session_state.responses = {}
if "progress" not in st.session_state:
    st.session_state.progress = 0
if "resume_content" not in st.session_state:
    st.session_state.resume_content = None
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False
if "current_action" not in st.session_state:
    st.session_state.current_action = None
if "learning_path" not in st.session_state:
    st.session_state.learning_path = None
if "skill_gaps" not in st.session_state:
    st.session_state.skill_gaps = None

def input_pdf_setup(uploaded_file):
    """Process PDF to base64 encoded images with error handling."""
    if uploaded_file is None:
        return None

    try:
        if not st.session_state.pdf_processed or "resume_content" not in st.session_state:
            pdf_bytes = uploaded_file.read()
            if not pdf_bytes:
                st.error("❌ Uploaded file is empty. Please upload a valid PDF.")
                return None

            images = pdf2image.convert_from_bytes(pdf_bytes)
            pdf_parts = []
            for img in images[:3]:  # Limit to first 3 pages
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_data = img_byte_arr.getvalue()
                pdf_parts.append({
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(img_data).decode()
                })
            st.session_state.resume_content = pdf_parts
            st.session_state.pdf_processed = True
            uploaded_file.seek(0)
        return st.session_state.resume_content
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        return None

# Function to generate skill gap and learning path using Gemini or fallback
def generate_skill_gap_learning_path(jd_input, pdf_content):
    """Generate personalized skill gap analysis and learning path."""
    if not check_and_reset_quota():
        return """[
            {"skill": "Data Analysis", "importance": 8, "difficulty": 6},
            {"skill": "Project Management", "importance": 7, "difficulty": 5},
            {"skill": "Cloud Computing", "importance": 9, "difficulty": 7},
            {"skill": "UI/UX Design", "importance": 6, "difficulty": 4},
            {"skill": "DevOps", "importance": 8, "difficulty": 8}
        ]""", """[
            {"milestone": "Data Analysis Fundamentals", "skills_addressed": ["Data Analysis"], "resources": ["Coursera Data Analysis Course", "Practice with Kaggle Datasets"], "duration_weeks": 3, "outcome": "Basic proficiency in data analysis"},
            {"milestone": "Project Management Certification", "skills_addressed": ["Project Management"], "resources": ["PMI Certification", "Agile Methodology Course"], "duration_weeks": 4, "outcome": "Project management certification"},
            {"milestone": "Cloud Computing Basics", "skills_addressed": ["Cloud Computing", "DevOps"], "resources": ["AWS Training", "Azure Learning Path"], "duration_weeks": 5, "outcome": "Cloud computing fundamentals"}
        ]"""

    skill_gap_prompt = """
    Analyze the resume and job description. Identify EXACTLY 5 key skills or qualifications missing from the resume 
    that are required or preferred in the job description. Return ONLY a JSON formatted list with this structure:
    [{"skill": "skill name", "importance": 1-10, "difficulty": 1-10}]
    """
    learning_path_prompt = """
    Based on the identified skill gaps, create a learning path with 3-5 milestones to help the candidate acquire these skills.
    For each milestone, provide: specific resource recommendations (courses, certifications, practice projects), 
    estimated time to complete (in weeks), and expected proficiency level upon completion.
    Return ONLY a JSON formatted list with this structure:
    [{"milestone": "name", "skills_addressed": ["skill1", "skill2"], "resources": ["resource1", "resource2"], "duration_weeks": number, "outcome": "description"}]
    """
    
    skill_gaps_str = get_gemini_response(jd_input, pdf_content, skill_gap_prompt, temperature=0.3, max_tokens=1000)
    if "quota" in skill_gaps_str.lower():
        return """[
            {"skill": "Data Analysis", "importance": 8, "difficulty": 6},
            {"skill": "Project Management", "importance": 7, "difficulty": 5},
            {"skill": "Cloud Computing", "importance": 9, "difficulty": 7},
            {"skill": "UI/UX Design", "importance": 6, "difficulty": 4},
            {"skill": "DevOps", "importance": 8, "difficulty": 8}
        ]""", """[
            {"milestone": "Data Analysis Fundamentals", "skills_addressed": ["Data Analysis"], "resources": ["Coursera Data Analysis Course", "Practice with Kaggle Datasets"], "duration_weeks": 3, "outcome": "Basic proficiency in data analysis"},
            {"milestone": "Project Management Certification", "skills_addressed": ["Project Management"], "resources": ["PMI Certification", "Agile Methodology Course"], "duration_weeks": 4, "outcome": "Project management certification"},
            {"milestone": "Cloud Computing Basics", "skills_addressed": ["Cloud Computing", "DevOps"], "resources": ["AWS Training", "Azure Learning Path"], "duration_weeks": 5, "outcome": "Cloud computing fundamentals"}
        ]"""
    
    learning_path_str = get_gemini_response(
        f"Job Description: {jd_input}\nSkill Gaps: {skill_gaps_str}",
        pdf_content,
        learning_path_prompt,
        temperature=0.4,
        max_tokens=1500
    )
    return skill_gaps_str, learning_path_str

# Sidebar: Control Panel and API Usage
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    analysis_mode = st.radio("Analysis Mode", ["Basic", "Advanced"], index=1)
    visualization_type = st.selectbox("Visualization Style", ["Radial", "Linear", "3D"])
    
    st.markdown("---")
    quota_percentage = min(100, (st.session_state.api_call_count / st.session_state.quota_limit) * 100)
    st.markdown("### 📊 API Usage")
    st.progress(int(quota_percentage))
    st.markdown(f"**{st.session_state.api_call_count}/{st.session_state.quota_limit}** calls used")
    if quota_percentage > 70:
        remaining_minutes = 60 - ((datetime.now() - st.session_state.last_reset_time).seconds // 60)
        st.markdown(f"⏱️ Resets in: **{remaining_minutes}** minutes")
    
    st.markdown("---")
    with st.expander("🔍 Advanced Settings"):
        st.session_state.temperature = st.slider("AI Creativity", 0.0, 1.0, 0.7)
        st.session_state.response_length = st.selectbox("Response Length", ["Short", "Medium", "Detailed"])
        st.session_state.quota_limit = st.number_input("API Call Limit", min_value=10, max_value=200, value=60)
    st.markdown("---")
    st.markdown(
        f'<a href="#" class="resume-builder-link">🚀 Build Your Resume (Coming Soon)</a>',
        unsafe_allow_html=True
    )

# Main Processing Section
with st.container():
    st.markdown("## 📄 Resume Analyzer")
    with st.container():
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(" ", type=["pdf"], key="file_upload",
                                           on_change=lambda: st.session_state.update({"pdf_processed": False}))
        st.markdown("</div>", unsafe_allow_html=True)
        jd_input = st.text_area(" ", placeholder="✍️ Paste Job Description Here...", height=150)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🚀 Full Analysis", use_container_width=True):
            st.session_state.current_action = "analysis"
    with col2:
        if st.button("💎 Smart Enhance", use_container_width=True):
            st.session_state.current_action = "enhance"
    with col3:
        if st.button("🎯 Match Score", use_container_width=True):
            st.session_state.current_action = "match"
    with col4:
        if st.button("🔮 Skill Gap Simulator", use_container_width=True):
            st.session_state.current_action = "skill_gap"

    if quota_percentage > 90:
        st.markdown("""
        <div class="quota-warning">
            ⚠️ API quota almost exhausted. Some features may use cached responses.
        </div>
        """, unsafe_allow_html=True)

    if "current_action" in st.session_state:
        if uploaded_file and jd_input:
            with st.spinner("🧠 Analyzing with Gemini AI..."):
                progress_bar = st.progress(0)
                pdf_content = input_pdf_setup(uploaded_file)
                if pdf_content:
                    temperature = st.session_state.get('temperature', 0.7)
                    response_length = st.session_state.get('response_length', 'Medium')
                    length_mapping = {"Short": 500, "Medium": 1000, "Detailed": 2000}
                    max_tokens = length_mapping.get(response_length, 1000)
                    
                    if st.session_state.current_action == "skill_gap":
                        for i in range(50):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        skill_gaps_str, learning_path_str = generate_skill_gap_learning_path(jd_input, pdf_content)
                        st.session_state.skill_gaps = skill_gaps_str
                        st.session_state.learning_path = learning_path_str
                        for i in range(50, 100):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        st.markdown("### 🛠️ Skill Gap Analysis")
                        try:
                            import json, re
                            skill_gaps_str = re.search(r'\[.*\]', skill_gaps_str, re.DOTALL)
                            skill_gaps_str = skill_gaps_str.group(0) if skill_gaps_str else "[]"
                            skill_gaps = json.loads(skill_gaps_str)
                            learning_path_str = re.search(r'\[.*\]', learning_path_str, re.DOTALL)
                            learning_path_str = learning_path_str.group(0) if learning_path_str else "[]"
                            learning_path = json.loads(learning_path_str)
                            
                            labels = [item.get('skill', f'Skill {i+1}') for i, item in enumerate(skill_gaps)]
                            importance = [item.get('importance', 5) for item in skill_gaps]
                            difficulty = [item.get('difficulty', 5) for item in skill_gaps]
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatterpolar(
                                r=importance,
                                theta=labels,
                                fill='toself',
                                name='Importance',
                                line_color='#E5BEEC',
                                fillcolor='rgba(229, 190, 236, 0.3)'
                            ))
                            fig.add_trace(go.Scatterpolar(
                                r=difficulty,
                                theta=labels,
                                fill='toself',
                                name='Difficulty',
                                line_color='#917FB3',
                                fillcolor='rgba(145, 127, 179, 0.3)'
                            ))
                            fig.update_layout(
                                polar=dict(
                                    radialaxis=dict(visible=True, range=[0, 10])
                                ),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                showlegend=True
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            for i, skill in enumerate(skill_gaps):
                                st.markdown(f"""
                                <div class="skill-gap-card">
                                    <h4>{skill.get('skill', f'Skill {i+1}')}</h4>
                                    <div>Importance: {skill.get('importance', 'N/A')}/10</div>
                                    <div>Difficulty: {skill.get('difficulty', 'N/A')}/10</div>
                                </div>
                                """, unsafe_allow_html=True)
                            st.markdown('<div class="learning-path-title">🚀 Personalized Learning Path</div>', unsafe_allow_html=True)
                            total_weeks = sum(item.get('duration_weeks', 2) for item in learning_path)
                            st.markdown(f"**Estimated Time to Job Readiness: {total_weeks} weeks**")
                            current_week = 0
                            for i, milestone in enumerate(learning_path):
                                duration = milestone.get('duration_weeks', 2)
                                end_week = current_week + duration
                                st.markdown(f"""
                                <div class="learning-milestone">
                                    <h4>Milestone {i+1}: {milestone.get('milestone', f'Step {i+1}')} (Weeks {current_week+1}-{end_week})</h4>
                                    <p><strong>Skills addressed:</strong> {', '.join(milestone.get('skills_addressed', ['N/A']))}</p>
                                    <p><strong>Resources:</strong> {', '.join(milestone.get('resources', ['N/A']))}</p>
                                    <p><strong>Outcome:</strong> {milestone.get('outcome', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                current_week = end_week
                        except Exception as e:
                            st.error(f"Error parsing AI response: {str(e)}")
                    else:
                        # Original actions with fallback responses if quota is low
                        if not check_and_reset_quota():
                            if st.session_state.current_action == "match":
                                response = "Match Score: 72%"
                            elif st.session_state.current_action == "enhance":
                                response = get_career_advice("resume_improvement", "")
                            else:
                                response = """## Resume Analysis Summary

**Strengths:**
- Strong technical skills section
- Clear work experience chronology 
- Education credentials well presented

**Areas for Improvement:**
- Add more quantifiable achievements
- Enhance professional summary
- Consider adding relevant certifications

Your resume shows good potential but could benefit from more specific metrics and achievements to stand out to employers."""
                        else:
                            response = get_gemini_response(
                                jd_input,
                                pdf_content,
                                (f"Perform {st.session_state.current_action} analysis. " +
                                 ("Return match score as percentage only." if st.session_state.current_action == "match" else "")),
                                temperature=temperature,
                                max_tokens=max_tokens
                            )
                        for i in range(100):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        if st.session_state.current_action == "match":
                            try:
                                score = int(''.join(filter(str.isdigit, response)) or 50)
                                score = max(0, min(100, score))
                            except ValueError:
                                score = 50
                            fig = px.pie(values=[score, 100-score], names=["Match", "Gap"],
                                         hole=0.6, color_discrete_sequence=["#917FB3", "#2D2D2D"])
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.markdown(f"<div style='background: #2D2D2D; padding: 1rem; border-radius: 15px;'>{response}</div>", unsafe_allow_html=True)
                else:
                    st.error("❌ Failed to process PDF. Please check the file and try again.")
        else:
            st.warning("⚠️ Please upload resume and enter job description")

 # Chat Interface Section – Improved UI
st.markdown("## 💬 AI Career Advisor")

# Chat input area using a multi-line text area for longer queries
chat_input = st.text_area("Your question...", placeholder="Ask me anything about your resume...", key="chat_input", height=100)

if st.button("Ask AI", key="chat_ask"):
    if chat_input and uploaded_file:
        with st.spinner("💭 Processing..."):
            try:
                pdf_content = input_pdf_setup(uploaded_file)
                # First try local analysis
                local_analysis = analyze_resume_locally(pdf_content) if pdf_content else {}
                if "add" in chat_input.lower() and "resume" in chat_input.lower():
                    if local_analysis.get("skills"):
                        response = (
                            "**Based on your resume:**\n\n"
                            "Consider adding:\n"
                            f"- {random.choice(local_analysis.get('suggestions', ['more details about your projects']))}\n\n"
                            f"Found skills: {', '.join(local_analysis.get('skills', [])[:3])}"
                        )
                    else:
                        response = get_career_advice("resume_improvement", "")
                elif "job vacancy" in chat_input.lower():
                    response = (
                        "🔍 Latest Job Portals:\n"
                        "- [LinkedIn Jobs](https://linkedin.com/jobs)\n"
                        "- [Indeed](https://indeed.com)\n\n"
                        f"*Try searching for: {', '.join(local_analysis.get('skills', ['Python', 'Data Analysis']))}*"
                    )
                else:
                    response = get_gemini_response(
                        chat_input, 
                        pdf_content,
                        "Provide career advice based on the resume. Keep responses concise and actionable.",
                        temperature=0.3
                    )
                st.session_state.chat_history.append(("user", chat_input))
                st.session_state.chat_history.append(("bot", response))
            except Exception as e:
                st.error("⚠️ System busy. Please try simpler questions.")
    else:
        st.error("Please provide a query and upload your resume.")

# Chat display container with fixed height and dynamic scrolling
chat_display_container = st.container()
with chat_display_container:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for sender, message in st.session_state.chat_history:
        if sender == "user":
            st.markdown(
                f"<div class='chat-user'>👤 <strong>You:</strong> {message}</div>",
                unsafe_allow_html=True
            )
        else:
            # Format bot response as a bullet-point list if multi-line
            formatted_response = "<ul>" + "".join(
                f"<li>{line.strip()}</li>" for line in message.split('\n') if line.strip()
            ) + "</ul>"
            st.markdown(
                f"<div class='chat-bot'>🤖 <strong>Advisor:</strong> {formatted_response}</div>",
                unsafe_allow_html=True
            )
    st.markdown("</div>", unsafe_allow_html=True)

 
st.markdown("---")
st.markdown("<div style='text-align: center; color: var(--accent);'>Powered by Gemini AI | ✨ Precision Hiring Solutions</div>", unsafe_allow_html=True)
