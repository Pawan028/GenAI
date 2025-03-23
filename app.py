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


# Load environment variables
load_dotenv()

# Configure Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-1.5-pro"

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

    /* Enhanced Logo and Header */
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

    /* Keep existing interactive elements */
    .upload-section:hover {
        border-color: var(--accent) !important;
        background: rgba(145, 127, 179, 0.1) !important;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(229, 190, 236, 0.3);
    }

    /* Enhanced Logo Image */
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

    /* Rest of existing styles remain unchanged */
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
    }

    /* New Timeline Styling */
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
</style>
""", unsafe_allow_html=True)

# Add this header code where your original header was
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

def get_gemini_response(user_input, pdf_content, prompt, temperature=0.7, max_tokens=1000):
    """Get response from Gemini AI with error handling and config"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            [user_input, *pdf_content, prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        return response.text
    except Exception as e:
        return f"❌ Error: {str(e)}"

def input_pdf_setup(uploaded_file):
    """Process PDF to base64 encoded images with better error handling"""
    if uploaded_file is None:
        return None

    try:
        # Check if PDF needs reprocessing
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
            uploaded_file.seek(0)  # Reset file pointer
            
        return st.session_state.resume_content
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        return None

# Function to generate skill gap and learning path
def generate_skill_gap_learning_path(jd_input, pdf_content):
    """Generate personalized skill gap analysis and learning path"""
    skill_gap_prompt = """
    Analyze the resume and job description. Identify EXACTLY 5 key skills or qualifications missing from the resume 
    that are required or preferred in the job description. Return ONLY a JSON formatted list with this structure:
    [{"skill": "skill name", "importance": 1-10, "difficulty": 1-10}]
    Where importance is how critical the skill is for the job, and difficulty is how hard it is to acquire.
    """
    
    learning_path_prompt = """
    Based on the identified skill gaps, create a learning path with 3-5 milestones to help the candidate acquire these skills.
    For each milestone, provide: specific resource recommendations (courses, certifications, practice projects), 
    estimated time to complete (in weeks), and expected proficiency level upon completion.
    Return ONLY a JSON formatted list with this structure:
    [{"milestone": "name", "skills_addressed": ["skill1", "skill2"], "resources": ["resource1", "resource2"], "duration_weeks": number, "outcome": "description"}]
    """
    
    # Get skill gaps
    skill_gaps_str = get_gemini_response(
        jd_input,
        pdf_content,
        skill_gap_prompt,
        temperature=0.3,
        max_tokens=1000
    )
    
    # Get learning path
    learning_path_str = get_gemini_response(
        f"Job Description: {jd_input}\nSkill Gaps: {skill_gaps_str}",
        pdf_content,
        learning_path_prompt,
        temperature=0.4,
        max_tokens=1500
    )
    
    return skill_gaps_str, learning_path_str

# Add this in your sidebar section where you want the resume builder link
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    analysis_mode = st.radio("Analysis Mode", ["Basic", "Advanced"], index=1)
    visualization_type = st.selectbox("Visualization Style", ["Radial", "Linear", "3D"])
    st.markdown("---")
    with st.expander("🔍 Advanced Settings"):
        st.session_state.temperature = st.slider("AI Creativity", 0.0, 1.0, 0.7)
        st.session_state.response_length = st.selectbox("Response Length", ["Short", "Medium", "Detailed"])
    st.markdown("---")
    st.markdown(
        f'<a href="http://localhost:3000/" class="resume-builder-link">🚀 Build Your Resume</a>',
        unsafe_allow_html=True
    )

# Modified Processing Section
with st.container():
    # Resume Upload Section
    st.markdown("## 📄 Resume Analyzer")
    with st.container():
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(" ", type=["pdf"], key="file_upload",
                                        on_change=lambda: st.session_state.update({"pdf_processed": False}))
        st.markdown("</div>", unsafe_allow_html=True)
        jd_input = st.text_area(" ", placeholder="✍️ Paste Job Description Here...", height=150)

    # Action Cards
    col1, col2, col3, col4 = st.columns(4)  # Added fourth column for new feature
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

    # Results Display
    if "current_action" in st.session_state:
        if uploaded_file and jd_input:
            with st.spinner("🧠 Analyzing with Gemini AI..."):
                progress_bar = st.progress(0)
                pdf_content = input_pdf_setup(uploaded_file)
                
                if pdf_content:  # Only proceed if PDF processed successfully
                    # Get settings from sidebar
                    temperature = st.session_state.get('temperature', 0.7)
                    response_length = st.session_state.get('response_length', 'Medium')
                    
                    # Map response length to tokens
                    length_mapping = {"Short": 500, "Medium": 1000, "Detailed": 2000}
                    max_tokens = length_mapping.get(response_length, 1000)
                    
                    # Handle specific skill gap action
                    if st.session_state.current_action == "skill_gap":
                        # Progress bar animation for the first half
                        for i in range(50):
                            time.sleep(0.02)
                            progress_bar.progress(i + 1)
                            
                        # Generate skill gap and learning path
                        skill_gaps_str, learning_path_str = generate_skill_gap_learning_path(jd_input, pdf_content)
                        
                        # Save to session state
                        st.session_state.skill_gaps = skill_gaps_str
                        st.session_state.learning_path = learning_path_str
                        
                        # Progress bar animation for the second half
                        for i in range(50, 100):
                            time.sleep(0.02)
                            progress_bar.progress(i + 1)
                            
                        # Display the results in a more visually appealing way
                        st.markdown("### 🛠️ Skill Gap Analysis")
                        
                        # Try to clean and format the JSON output
                        try:
                            import json
                            import re
                            
                            # Clean and parse JSON strings
                            # (Remove any text before or after the JSON array)
                            skill_gaps_str = re.search(r'\[.*\]', skill_gaps_str, re.DOTALL)
                            skill_gaps_str = skill_gaps_str.group(0) if skill_gaps_str else "[]"
                            skill_gaps = json.loads(skill_gaps_str)
                            
                            learning_path_str = re.search(r'\[.*\]', learning_path_str, re.DOTALL)
                            learning_path_str = learning_path_str.group(0) if learning_path_str else "[]"
                            learning_path = json.loads(learning_path_str)
                            
                            # Display skill gaps as radar chart
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
                                    radialaxis=dict(
                                        visible=True,
                                        range=[0, 10]
                                    )
                                ),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                showlegend=True
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Display skill gap cards
                            for i, skill in enumerate(skill_gaps):
                                st.markdown(f"""
                                <div class="skill-gap-card">
                                    <h4>{skill.get('skill', f'Skill {i+1}')}</h4>
                                    <div>Importance: {skill.get('importance', 'N/A')}/10</div>
                                    <div>Difficulty: {skill.get('difficulty', 'N/A')}/10</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Display learning path timeline
                            st.markdown('<div class="learning-path-title">🚀 Personalized Learning Path</div>', unsafe_allow_html=True)
                            
                            # Calculate total weeks
                            total_weeks = sum(item.get('duration_weeks', 2) for item in learning_path)
                            
                            st.markdown(f"**Estimated Time to Job Readiness: {total_weeks} weeks**")
                            
                            # Timeline visualization
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
                            
                        except (json.JSONDecodeError, Exception) as e:
                            st.error(f"Error parsing AI response: {str(e)}")
                            st.text("Raw skill gaps data:")
                            st.text(skill_gaps_str)
                            st.text("Raw learning path data:")
                            st.text(learning_path_str)
                    else:
                        # Handle original actions
                        response = get_gemini_response(
                            jd_input,
                            pdf_content,
                            (f"Perform {st.session_state.current_action} analysis. " +
                            ("Return match score as percentage only." 
                                if st.session_state.current_action == "match" else "")),
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        
                        # Progress bar animation
                        for i in range(100):
                            time.sleep(0.02)
                            progress_bar.progress(i + 1)
                        
                        # Enhanced Visualization
                        if st.session_state.current_action == "match":
                            try:
                                score = int(''.join(filter(str.isdigit, response)) or 50)
                                score = max(0, min(100, score))  # Ensure valid percentage
                            except ValueError:
                                score = 50
                            fig = px.pie(values=[score, 100-score], 
                                        names=["Match", "Gap"],
                                        hole=0.6,
                                        color_discrete_sequence=["#917FB3", "#2D2D2D"])
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.markdown(
                                f"<div style='background: #2D2D2D; padding: 1rem; border-radius: 15px;'>{response}</div>", 
                                unsafe_allow_html=True
                            )
                else:
                    st.error("❌ Failed to process PDF. Please check the file and try again.")
        else:
            st.warning("⚠️ Please upload resume and enter job description")

# Enhanced Chat Interface
st.markdown("## 💬 AI Career Advisor")
chat_input = st.text_input(" ", placeholder="Ask me anything about your resume...", key="chat_input")

if st.button("Ask AI", key="chat_ask"):
    if chat_input and uploaded_file:
        with st.spinner("💭 Processing..."):
            pdf_content = input_pdf_setup(uploaded_file)
            if pdf_content:
                response = get_gemini_response(
                    chat_input, 
                    pdf_content,
                    "Provide career advice based on the resume",
                    temperature=0.3  # More conservative for career advice
                )
                st.session_state.chat_history.append(("user", chat_input))
                st.session_state.chat_history.append(("bot", response))
            else:
                st.error("❌ No valid resume content to analyze")

# Add this section to display chat history
for sender, message in st.session_state.chat_history:
    if sender == "user":
        st.markdown(f"<div class='chat-user'>👤 {message}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bot'>🤖 {message}</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: var(--accent);'>Powered by Gemini AI | ✨ Precision Hiring Solutions</div>", 
            unsafe_allow_html=True)