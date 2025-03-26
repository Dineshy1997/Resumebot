import os
import re
import json
import asyncio
import base64
import streamlit as st
import pdfplumber
import google.generativeai as genai
from urllib.parse import quote
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import datetime
import time
from streamlit_extras.colored_header import colored_header
from streamlit_extras.stateful_button import button
from streamlit_lottie import st_lottie
import requests
import difflib
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="CyTibot Resume Filtering",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS styles with updated lighter color gradients
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Poppins:wght@400;600&display=swap');

    /* Main UI elements */
    .stApp {
        background: linear-gradient(to bottom, #e6f0fa, #c3e0f5); /* Lighter blue gradient */
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        color: #1e88e5 !important; /* Bright blue for headers */
    }
    /* Bolder form labels */
    label.stFormFieldLabel {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1e88e5;
        font-family: 'Poppins', sans-serif;
    }
    /* Individual feature table styling */
    .feature-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 2rem;
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .feature-table:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15);
    }
    .feature-table th {
        padding: 1.2rem;
        text-align: left;
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(90deg, #42a5f5, #90caf9); /* Lighter blue gradient for feature header */
        color: #ffffff;
        font-size: 1.4rem;
        font-weight: 600;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
    }
    /* Button styling */
    .stButton button {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
        background-color: #ff8a65 !important; /* Lighter coral for buttons */
        color: #ffffff !important;
        border: none !important;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        background-color: #ff7043 !important; /* Slightly darker coral on hover */
    }
    /* Primary action buttons */
    .primary-btn button {
        background-color: #42a5f5 !important; /* Bright blue */
        color: white !important;
    }
    .primary-btn button:hover {
        background-color: #1e88e5 !important; /* Slightly darker blue on hover */
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e6f0fa !important; /* Lighter blue background for tabs */
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 4px 4px 0px 0px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #c3e0f5 !important; /* Lighter blue for tab */
        color: #1e88e5 !important;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #42a5f5 !important; /* Active tab in bright blue */
        color: #ffffff !important;
    }
    /* Metric styling */
    [data-testid="stMetric"] {
        background-color: #ffe0b2 !important; /* Light peach for metrics */
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.2rem !important;
        font-weight: 600;
        color: #ef6c00 !important; /* Darker orange for metric labels */
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        color: #ef6c00 !important;
    }
    /* Data editor */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        background-color: #fff;
    }
    /* File uploader */
    .stFileUploader > div:first-child {
        width: 100%;
        background-color: #e6f0fa !important; /* Lighter blue for uploader */
        border-radius: 8px;
    }
    /* Logo styling */
    .logo-text {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'Montserrat', sans-serif;
        background: linear-gradient(90deg, #42a5f5, #ff8a65); /* Lighter blue to coral gradient */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .logo-container {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    /* Progress bar */
    .stProgress > div > div {
        background-color: #ff8a65 !important; /* Lighter coral for progress bar */
    }
    /* General text inputs and areas */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #e6f0fa !important; /* Lighter blue for inputs */
        color: #1565c0 !important;
        font-family: 'Poppins', sans-serif;
        font-size: 1.1rem;
    }
    /* Expander styling */
    .stExpander {
        background-color: #e6f0fa !important; /* Lighter blue for expanders */
        border-radius: 8px;
    }
    .stExpander > div > div > div > p {
        color: #1565c0 !important;
        font-family: 'Poppins', sans-serif;
        font-size: 1.1rem;
    }
    /* Slider styling */
    .stSlider [data-baseweb="slider"] > div > div > div {
        background-color: #ff8a65 !important; /* Lighter coral for slider */
    }
    /* Second page background */
    .second-page {
        background: linear-gradient(to bottom, #ffe0b2, #ffcc80); /* Light peach gradient */
        padding: 2rem;
        border-radius: 10px;
    }
    /* Chat container */
    .chat-container {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        max-height: 500px;
        overflow-y: auto;
        margin-bottom: 1rem;
    }
    .chat-message {
        margin-bottom: 1rem;
        padding: 0.8rem;
        border-radius: 8px;
        font-family: 'Poppins', sans-serif;
        font-size: 1rem;
    }
    .chat-message.agent {
        background-color: #e6f0fa;
        color: #1565c0;
        margin-left: 20%;
        margin-right: 5%;
    }
    .chat-message.candidate {
        background-color: #ffe0b2;
        color: #ef6c00;
        margin-right: 20%;
        margin-left: 5%;
    }
    /* Alert message styling */
    .alert-message {
        background-color: #ffcccb;
        color: #d32f2f;
        padding: 0.8rem;
        border-radius: 8px;
        font-family: 'Poppins', sans-serif;
        font-size: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Directory for storing resumes
UPLOAD_DIRECTORY = "uploaded_resumes"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Initialize session state variables
if 'filtered_results' not in st.session_state:
    st.session_state.filtered_results = pd.DataFrame()
if 'email_configured' not in st.session_state:
    st.session_state.email_configured = False
if 'sender_email' not in st.session_state:
    st.session_state.sender_email = ""
if 'sender_password' not in st.session_state:
    st.session_state.sender_password = ""
if 'has_shown_welcome' not in st.session_state:
    st.session_state.has_shown_welcome = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📝 Resume Filtering"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}
if 'current_candidate' not in st.session_state:
    st.session_state.current_candidate = None
if 'candidate_skills' not in st.session_state:
    st.session_state.candidate_skills = []
if 'response_timer' not in st.session_state:
    st.session_state.response_timer = {}
if 'eye_movement_alert' not in st.session_state:
    st.session_state.eye_movement_alert = False

# API Keys with Rotation
API_KEYS = [
    "AIzaSyD4tsIWNqLI8tzRwvK15YmFLtK8dSR_jX0",
    "AIzaSyBP6yImGa3PpnmI1-KeyuFd1BZNWkSoFm0",
    "<YOUR_API_KEY_3>",
    "<YOUR_API_KEY_4>"
]
current_api_index = 0

# Lottie animations
def load_lottie_url(url):
    """Load lottie animation from URL"""
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Load HR management-related animation
lottie_hr = load_lottie_url("https://assets1.lottiefiles.com/packages/lf20_3p3ruewe.json")  # HR management animation
lottie_email = load_lottie_url("https://assets5.lottiefiles.com/packages/lf20_u25cckyh.json")
lottie_success = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_s1evqrqq.json")

def set_api_key():
    """Set the current API key for the AI service"""
    global current_api_index
    genai.configure(api_key=API_KEYS[current_api_index])

def rotate_api_key():
    """Rotate to the next API key in the list"""
    global current_api_index
    current_api_index = (current_api_index + 1) % len(API_KEYS)
    set_api_key()

# Initialize API key
set_api_key()

def extract_text_from_pdf(pdf_path):
    """Extract **powerful insights** from a PDF file"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
    return text

def get_pdf_download_link(file_path, file_name):
    """Generate a sleek download link for a PDF file"""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        href = f'<a href="data:application/pdf;base64,{base64_pdf}" download="{file_name}" target="_blank" style="text-decoration:none"><span style="background-color:#e6f0fa; color:#1565c0; padding:5px 10px; border-radius:4px; font-size:0.9rem; display:inline-flex; align-items:center;"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-file-earmark-pdf-fill" viewBox="0 0 16 16" style="margin-right:5px"><path d="M5.523 12.424c.14-.082.293-.162.459-.238a7.878 7.878 0 0 1-.45.606c-.28.337-.498.516-.635.572a.266.266 0 0 1-.035.012.282.282 0 0 1-.026-.044c-.056-.11-.054-.216.04-.36.106-.165.319-.354.647-.548zm2.455-1.647c-.119.025-.237.05-.356.078a21.148 21.148 0 0 0 .5-1.05 12.045 12.045 0 0 0 .51.858c-.217.032-.436.07-.654.114zm2.525.939a3.881 3.881 0 0 1-.435-.41c.228.005.434.022.612.054.317.057.466.147.518.209a.095.095 0 0 1 .026.064.436.436 0 0 1-.06.2.307.307 0 0 1-.094.124.107.107 0 0 1-.069.015c-.09-.003-.258-.066-.498-.256zM8.278 6.97c-.04.244-.108.524-.2.829a4.86 4.86 0 0 1-.089-.346c-.076-.353-.087-.63-.046-.822.038-.177.11-.248.196-.283a.517.517 0 0 1 .145-.04c.013.03.028.092.032.198.005.122-.007.277-.038.465z"/><path fill-rule="evenodd" d="M4 0h5.293A1 1 0 0 1 10 .293L13.707 4a1 1 0 0 1 .293.707V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm5.5 1.5v2a1 1 0 0 0 1 1h2l-3-3zM4.165 13.668c.09.18.23.343.438.419.207.075.412.04.58-.03.318-.13.635-.436.926-.786.333-.401.683-.927 1.021-1.51a11.651 11.651 0 0 1 1.997-.406c.3.383.61.713.91.95.28.22.603.403.934.417a.856.856 0 0 0 .51-.138c.155-.101.27-.247.354-.416.09-.181.145-.37.138-.563a.844.844 0 0 0-.2-.518c-.226-.27-.596-.4-.96-.465a5.76 5.76 0 0 0-1.335-.05 10.954 10.954 0 0 1-.98-1.686c.25-.66.437-1.284.52-1.794.036-.218.055-.426.048-.614a1.238 1.238 0 0 0-.127-.538.7.7 0 0 0-.477-.365c-.202-.043-.41 0-.601.077-.377.15-.576.47-.651.823-.073.34-.04.736.046 1.136.088.406.238.848.43 1.295a19.697 19.697 0 0 1-1.062 2.227 7.662 7.662 0 0 0-1.482.645c-.37.22-.699.48-.897.787-.21.326-.275.714-.08 1.103z"/></svg> View</span></a>'
        return href
    except Exception as e:
        st.error(f"Error creating download link: {e}")
        return "Link Error"

def extract_contact_info_and_name(resume_text):
    """Unleash candidate details with precision"""
    if not resume_text:
        return "N/A", "N/A", "N/A"
        
    email_pattern = r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+'
    emails = re.findall(email_pattern, resume_text)
    
    phone_pattern = re.compile(r"""
        (?:
            (?:\+\d{1,3}[\s\-\.]?)?                # Optional country code with +
            (?:\(?\d{1,4}\)?[\s\-\.]?)?           # Optional area code, possibly in parentheses
            \d{3}[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}  # Main number groups
            |
            \d{10,12}                             # Simple 10-12 digit number
        )
    """, re.VERBOSE)
    
    phone_candidates = re.findall(phone_pattern, resume_text)
    phones = [re.sub(r'[\s\-\.\(\)]', '', p) for p in phone_candidates if len(re.sub(r'[\s\-\.\(\)]', '', p)) >= 7]
    
    email = emails[0] if emails else "N/A"
    phone = phones[0] if phones else "N/A"

    name = resume_text.split('\n')[0] if resume_text else "N/A"
    if len(name) > 50 or name == "N/A":
        name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
        names = re.findall(name_pattern, resume_text)
        name = names[0] if names else "N/A"
    
    return name.strip(), email, phone

async def analyze_resume(resume_text, job_description, min_experience, min_ats_score):
    """Tap into AI brilliance to match resumes with jobs"""
    prompt = f"""
    Compare the following resume with the job description:

    JOB DESCRIPTION:
    {job_description}

    RESUME:
    {resume_text}

    You MUST return a valid JSON object with exactly the following structure and nothing else:
    {{
        "ats_score": (number between 0 to 100),
        "meets_requirements": (true/false),
        "match_details": "Brief explanation highlighting matches or mismatches",
        "extracted_skills": "Comma-separated list of relevant skills found in the resume",
        "total_years_experience": (integer representing total years of work experience, rounded to nearest whole number),
        "key_strengths": "3-5 bullet points about candidate's key strengths"
    }}
    
    Do not include any explanations, conversations, or additional text outside the JSON object.
    """

    while True:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            json_text = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_text:
                result = json.loads(json_text.group())
            else:
                rotate_api_key()
                prompt += "\n\nIMPORTANT: You MUST return ONLY a valid JSON object with no additional text."
                continue

            result.setdefault("ats_score", 0)
            result.setdefault("meets_requirements", False)
            result.setdefault("match_details", "Not analyzed")
            result.setdefault("extracted_skills", "")
            result.setdefault("total_years_experience", 0)
            result.setdefault("key_strengths", "Not analyzed")

            if not isinstance(result["total_years_experience"], int):
                try:
                    result["total_years_experience"] = round(float(result["total_years_experience"]))
                except (ValueError, TypeError):
                    result["total_years_experience"] = 0

            experience_requirement_met = result["total_years_experience"] >= min_experience
            
            return {
                "is_match": result["meets_requirements"] and result["ats_score"] >= min_ats_score and experience_requirement_met,
                "ats_score": result["ats_score"],
                "match_details": result["match_details"],
                "extracted_skills": result["extracted_skills"],
                "total_years_experience": result["total_years_experience"],
                "key_strengths": result["key_strengths"]
            }
        except Exception as e:
            if "429" in str(e):
                rotate_api_key()
            else:
                st.error(f"AI API Error: {e}")
                return None

async def generate_interview_question(skills, previous_messages):
    """Generate a skill-based interview question using AI"""
    skills_list = skills.split(",") if skills else []
    skills_str = ", ".join([skill.strip() for skill in skills_list if skill.strip()])
    
    prompt = f"""
    You are an AI-powered interview assistant for CyTibot, a professional hiring platform. Your task is to generate a single, relevant interview question based on the candidate's skills and the conversation history. The question should be professional, engaging, and focused on assessing the candidate's expertise in one of their skills.

    Candidate Skills: {skills_str}
    Conversation History: {previous_messages}

    Return only the interview question as a string. Do not include any additional text, explanations, or JSON formatting.
    """

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        if "429" in str(e):
            rotate_api_key()
            return await generate_interview_question(skills, previous_messages)
        else:
            st.error(f"Error generating interview question: {e}")
            return "Can you tell me about a challenging project you worked on?"

async def check_copy_paste(response):
    """Check if the candidate's response is a copy-paste from common sources"""
    common_phrases = [
        "I am a highly motivated individual with a strong background in",
        "My experience includes working on projects that involve",
        "I have a proven track record of success in",
        "According to my research, the best approach is",
        "I found that the most effective way to handle this is"
    ]
    
    for phrase in common_phrases:
        similarity = difflib.SequenceMatcher(None, response.lower(), phrase.lower()).ratio()
        if similarity > 0.9:
            return True, f"Response appears to be copied: '{response}' matches common phrase '{phrase}'."
    
    # Check for AI-generated patterns
    ai_patterns = [
        "as an AI language model",
        "based on the information provided",
        "in my analysis",
        "I can provide a general overview"
    ]
    for pattern in ai_patterns:
        if pattern.lower() in response.lower():
            return True, f"Response appears to be AI-generated: contains pattern '{pattern}'."
    
    return False, ""

def send_email(sender_email, sender_password, recipient_email, subject, body, attachment_path=None, smtp_server="smtp.gmail.com", smtp_port=587):
    """Send **dynamic emails** with flair and attachments"""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

# Video processor for eye movement and face turning detection
class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.prev_face_position = None
        self.prev_eye_position = None
        self.alert_triggered = False

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        face_detected = False
        eye_detected = False
        movement_detected = False
        
        for (x, y, w, h) in faces:
            face_detected = True
            face_position = (x + w//2, y + h//2)
            
            # Check for face movement
            if self.prev_face_position:
                prev_x, prev_y = self.prev_face_position
                curr_x, curr_y = face_position
                if abs(curr_x - prev_x) > 50 or abs(curr_y - prev_y) > 50:
                    movement_detected = True
            
            self.prev_face_position = face_position
            
            # Detect eyes
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            for (ex, ey, ew, eh) in eyes:
                eye_detected = True
                eye_position = (x + ex + ew//2, y + ey + eh//2)
                
                # Check for eye movement
                if self.prev_eye_position:
                    prev_ex, prev_ey = self.prev_eye_position
                    curr_ex, curr_ey = eye_position
                    if abs(curr_ex - prev_ex) > 20 or abs(curr_ey - prev_ey) > 20:
                        movement_detected = True
                
                self.prev_eye_position = eye_position
                break
        
        if movement_detected and not self.alert_triggered:
            st.session_state.eye_movement_alert = True
            self.alert_triggered = True
        
        if not face_detected or not eye_detected:
            st.session_state.eye_movement_alert = True
            self.alert_triggered = True
        
        return frame

# Sidebar navigation
def sidebar():
    with st.sidebar:
        st.markdown('<div class="logo-container"><span class="logo-text">CyTibot</span></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("### **Explore the Magic**")
        st.markdown("- 📋 *Setup Your Job Posting*")
        st.markdown("- 📤 *Upload & Analyze Resumes*")
        st.markdown("- 📨 *Connect with Talent*")
        st.markdown("- ⚙️ *Configure Your Emails*")
        st.markdown("- 💬 *Interview Candidates*")
        
        st.markdown("---")
        
        if 'filtered_results' in st.session_state and not st.session_state.filtered_results.empty:
            st.markdown("### **Your Hiring Snapshot**")
            st.markdown(f"**Top Talent:** *{len(st.session_state.filtered_results)}*")
        
        st.markdown("---")
        st.markdown("### **Why CyTibot?**")
        st.markdown("""
        Discover the future of hiring with CyTibot:
        
        🌟 *Automate resume screening effortlessly*  
        🌟 *Unleash AI-powered talent matching*  
        🌟 *Send bulk emails with style*  
        🌟 *Conduct skill-based interviews*  
        🌟 *Build your dream team faster*  
        """)
        
        st.markdown("---")
        st.markdown("*Version 2.0 | © 2025 CyTibot*")

# Welcome screen with updated feature titles and HR animation
def show_welcome():
    if not st.session_state.has_shown_welcome:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("# Welcome to **CyTibot Resume Filtering** 🎯")
            st.markdown("""
            ### *Revolutionize Your Hiring with Cutting-Edge AI*
            
            With CyTibot, you can:
            - **Automate** *resume screening like never before*
            - **Discover** *top talent in seconds*
            - **Engage** *candidates with seamless communication*
            - **Interview** *candidates with skill-based chats*
            - **Transform** *your hiring into a breeze*
            """)
            
            if st.button("**Dive In Now →**", key="welcome_button"):
                st.session_state.has_shown_welcome = True
                st.rerun()
        
        with col2:
            if lottie_hr:
                st_lottie(lottie_hr, height=250, key="welcome_animation")
        
        st.markdown("---")
        
        # Define features data with actual titles
        features = [
            {"title": "🔍 Smart Analysis"},
            {"title": "⚡ ATS Precision"},
            {"title": "📊 Skill Spotlight"},
            {"title": "📧 Effortless Outreach"}
        ]
        
        # Display each feature in its own table
        for feature in features:
            st.markdown("""
            <table class="feature-table">
                <thead>
                    <tr>
                        <th>{}</th>
                    </tr>
                </thead>
            </table>
            """.format(feature['title']), unsafe_allow_html=True)
            
        return True
    return False

# Chat interface for first-round interview with specialized bot
def chat_interface(candidate_name, skills):
    st.markdown("### 💬 *First-Round Interview Chat*")
    st.markdown(f"**Candidate:** {candidate_name}")
    st.markdown(f"**Skills:** {skills}")

    # Enable live camera analysis
    st.markdown("### *Live Camera Analysis*")
    st.info("Please enable your camera to proceed with the interview. The system will monitor for eye movement and face turning.")
    
    webrtc_ctx = webrtc_streamer(
        key=f"video_{candidate_name}",
        video_processor_factory=VideoProcessor,
        rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
        media_stream_constraints={"video": True, "audio": False}
    )

    if st.session_state.eye_movement_alert:
        st.markdown('<div class="alert-message">⚠️ Suspicious behavior detected: Excessive eye movement or face turning. Please focus on the interview.</div>', unsafe_allow_html=True)
        st.session_state.eye_movement_alert = False  # Reset alert after displaying

    # Initialize chat history for this candidate
    if candidate_name not in st.session_state.chat_history:
        st.session_state.chat_history[candidate_name] = []
        st.session_state.chat_history[candidate_name].append({
            "role": "agent",
            "message": f"Hello {candidate_name}! I'm CyTibot, here to conduct your first-round interview. Let's get started with some questions about your skills. You have 2 minutes to respond to each question."
        })

    # Initialize response timer for this candidate
    if candidate_name not in st.session_state.response_timer:
        st.session_state.response_timer[candidate_name] = {
            "start_time": time.time(),
            "time_limit": 120  # 2 minutes in seconds
        }

    # Display chat history
    with st.container():
        chat_container = st.empty()
        with chat_container.container():
            for chat in st.session_state.chat_history[candidate_name]:
                if chat["role"] == "agent":
                    st.markdown(f'<div class="chat-message agent">{chat["message"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message candidate">{chat["message"]}</div>', unsafe_allow_html=True)

    # Display remaining time
    elapsed_time = time.time() - st.session_state.response_timer[candidate_name]["start_time"]
    remaining_time = max(0, st.session_state.response_timer[candidate_name]["time_limit"] - elapsed_time)
    st.markdown(f"**Time Remaining:** {int(remaining_time)} seconds")

    if remaining_time <= 0:
        st.markdown('<div class="alert-message">⚠️ Time limit exceeded! Moving to the next question.</div>', unsafe_allow_html=True)
        # Generate the next question
        previous_messages = "\n".join([f"{msg['role']}: {msg['message']}" for msg in st.session_state.chat_history[candidate_name]])
        next_question = asyncio.run(generate_interview_question(skills, previous_messages))
        st.session_state.chat_history[candidate_name].append({
            "role": "agent",
            "message": next_question
        })
        st.session_state.response_timer[candidate_name]["start_time"] = time.time()
        st.rerun()

    # Input for candidate response
    with st.form(key=f"chat_form_{candidate_name}", clear_on_submit=True):
        candidate_response = st.text_input("**Your Response**", placeholder="Type your answer here...", key=f"response_{candidate_name}")
        submit_button = st.form_submit_button("Send")

        if submit_button and candidate_response:
            # Check for copy-paste
            is_copied, copy_message = asyncio.run(check_copy_paste(candidate_response))
            if is_copied:
                st.markdown(f'<div class="alert-message">⚠️ {copy_message}</div>', unsafe_allow_html=True)
                st.session_state.chat_history[candidate_name].append({
                    "role": "agent",
                    "message": "Please provide an original response. Let's try another question."
                })
            else:
                # Add candidate's response to chat history
                st.session_state.chat_history[candidate_name].append({
                    "role": "candidate",
                    "message": candidate_response
                })

            # Generate the next question based on skills and conversation history
            previous_messages = "\n".join([f"{msg['role']}: {msg['message']}" for msg in st.session_state.chat_history[candidate_name]])
            next_question = asyncio.run(generate_interview_question(skills, previous_messages))

            # Add the next question to chat history
            st.session_state.chat_history[candidate_name].append({
                "role": "agent",
                "message": next_question
            })

            # Reset the timer
            st.session_state.response_timer[candidate_name]["start_time"] = time.time()
            st.rerun()

# Main App UI with "Return to Home" option
def main():
    sidebar()
    
    if show_welcome():
        return
    
    # Add "Return to Home" button
    if st.button("🏠 Return to Home"):
        st.session_state.has_shown_welcome = False
        st.rerun()
    
    st.markdown("---")
    
    # Define tabs
    tabs = st.tabs(["📝 *Resume Filtering*", "✉️ *Email Settings*", "💬 *Interview Candidates*"])
    
    # Resume Filtering Tab
    with tabs[0]:
        st.markdown('<div class="second-page">', unsafe_allow_html=True)
        
        colored_header(label="Job Position Setup", description="*Craft your perfect job criteria with ease*",
                      color_name="orange-70")
        
        job_description = st.text_area("**Job Description**",
                                      placeholder="Paste your job details here - skills, experience, and more...",
                                      help="*Fuel the AI with rich details to find your stars!*",
                                      height=150)
        
        st.markdown("### *Set Your Filters*")
        col1, col2 = st.columns(2)
        with col1:
            min_experience = st.number_input("**Minimum Experience (years)**", 
                                           min_value=0, value=2,
                                           help="Only the seasoned pros make the cut!")
        with col2:
            min_ats_score = st.slider("**Minimum ATS Score**", 
                                     min_value=0, max_value=100, value=70,
                                     help="Raise the bar for top-tier talent!")
        
        st.markdown("### *Upload Your Talent Pool*")
        
        uploaded_files = st.file_uploader(
            "**Drop Resumes Here (PDFs only)**",
            type=["pdf"],
            accept_multiple_files=True,
            help="*Drag, drop, and let the magic begin!*"
        )
        
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("🚀 *Launch Resume Analysis*", use_container_width=True):
            if not uploaded_files:
                st.error("⚠️ *Oops! Add at least one resume to kick things off!*")
            elif not job_description:
                st.error("⚠️ *We need a job description to work our magic!*")
            else:
                with st.spinner("🔍 *Unpacking resumes with AI brilliance...*"):
                    matching_resumes = []
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()

                    for idx, file in enumerate(uploaded_files):
                        try:
                            file_path = os.path.join(UPLOAD_DIRECTORY, file.name)
                            with open(file_path, "wb") as f:
                                f.write(file.read())

                            status_placeholder.info(f"*Scanning: {file.name}*")
                            resume_text = extract_text_from_pdf(file_path)
                            name, email, phone = extract_contact_info_and_name(resume_text)

                            analysis = asyncio.run(analyze_resume(
                                resume_text,
                                job_description,
                                min_experience,
                                min_ats_score
                            ))

                            if analysis and analysis["is_match"]:
                                download_link = get_pdf_download_link(file_path, file.name)
                                skills_list = analysis["extracted_skills"].split(",")
                                formatted_skills = ", ".join([skill.strip() for skill in skills_list if skill.strip()])
                                
                                result_dict = {
                                    "Name": name,
                                    "Email": email,
                                    "Phone": phone,
                                    "Experience": f"{analysis['total_years_experience']} years",
                                    "ATS Score": analysis["ats_score"],
                                    "Skills": formatted_skills,
                                    "Strengths": analysis["key_strengths"],
                                    "Resume": download_link,
                                    "Attachment": file_path,
                                    "Send Email": True
                                }
                                matching_resumes.append(result_dict)
                        except Exception as e:
                            st.error(f"Error processing {file.name}: {e}")
                        
                        progress_bar.progress((idx + 1) / len(uploaded_files))

                    status_placeholder.empty()

                if matching_resumes:
                    progress_bar.empty()
                    if lottie_success:
                        st_lottie(lottie_success, height=120, key="success_animation", speed=1.5)
                    
                    st.success(f"✅ *Wow! {len(matching_resumes)} out of {len(uploaded_files)} resumes are a perfect fit!*")
                    st.session_state.filtered_results = pd.DataFrame(matching_resumes)
                else:
                    st.warning("⚠️ *No matches yet! Tweak your filters for a winning lineup.*")
        st.markdown('</div>', unsafe_allow_html=True)

        # Display the filtered results table persistently if it exists
        if 'filtered_results' in st.session_state and not st.session_state.filtered_results.empty:
            st.markdown("---")
            colored_header(label="Matched Candidates", description=f"*Meet your {len(st.session_state.filtered_results)} shining stars!*",
                          color_name="orange-70")
            
            display_df = st.session_state.filtered_results.drop(columns=["Attachment"])
            
            edited_df = st.data_editor(
                display_df,
                column_config={
                    "Send Email": st.column_config.CheckboxColumn(
                        "Send Email",
                        help="Check to reach out to this talent!",
                        default=True,
                    ),
                    "Resume": st.column_config.Column(
                        "Resume",
                        help="Peek at their brilliance!",
                        width="small",
                    ),
                    "ATS Score": st.column_config.ProgressColumn(
                        "ATS Score",
                        help="See how they stack up!",
                        format="%d%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True,
                use_container_width=True
            )
            
            if "Send Email" in edited_df.columns:
                for i, row in edited_df.iterrows():
                    if i < len(st.session_state.filtered_results):
                        st.session_state.filtered_results.at[i, "Send Email"] = row["Send Email"]
            
            colored_header(label="Results Summary", description="*A quick glance at your hiring success!*",
                          color_name="orange-30")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("**Total Resumes**", len(uploaded_files) if uploaded_files else 0)
            with col2:
                st.metric("**Qualified Talent**", len(st.session_state.filtered_results), 
                          f"{int(len(st.session_state.filtered_results)/(len(uploaded_files) if uploaded_files else 1)*100)}%")
            with col3:
                st.metric("**Rejected Resumes**", (len(uploaded_files) if uploaded_files else 0) - len(st.session_state.filtered_results))

        # Candidate Communications Section
        if 'filtered_results' in st.session_state and not st.session_state.filtered_results.empty:
            st.markdown("---")
            colored_header(label="Candidate Communications", description="*Reach out to your top picks with style!*",
                          color_name="orange-70")
            
            if not st.session_state.email_configured:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.warning("⚠️ *Hold on! Set up your email first in the Email Settings tab.*")
                with col2:
                    if st.button("**Jump to Email Settings →**", key="jump_to_email"):
                        st.session_state.active_tab = "✉️ Email Settings"
                        st.rerun()
            else:
                selected_candidates = st.session_state.filtered_results[st.session_state.filtered_results["Send Email"] == True]
                
                if selected_candidates.empty:
                    st.info("*No candidates selected yet. Check some boxes to get started!*")
                else:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        email_type = st.radio(
                            "**Choose Your Message**",
                            ["Interview Invitation", "Application Status Update"],
                            horizontal=True,
                            help="*Pick the vibe you want to send!*"
                        )
                    with col2:
                        if lottie_email:
                            st_lottie(lottie_email, height=100, key="email_animation")
                    
                    st.markdown("""
                    <div style="background-color: #e6f0fa; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 10px 0 rgba(0,0,0,0.1); margin-bottom: 1rem;">
                    """, unsafe_allow_html=True)
                    
                    if email_type == "Interview Invitation":
                        st.markdown("### 📅 *Plan an Epic Interview*")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            interview_date = st.date_input(
                                "**Interview Date**",
                                datetime.date.today() + datetime.timedelta(days=7),
                                min_value=datetime.date.today(),
                                help="Pick a day to meet your stars!"
                            )
                        with col2:
                            interview_time = st.text_input(
                                "**Interview Time**",
                                "10:00 AM",
                                help="Set the perfect time slot!"
                            )
                        with col3:
                            interview_location = st.text_input(
                                "**Interview Location**",
                                placeholder="Office or 'Virtual'",
                                help="Where will the magic happen?"
                            )
                        
                        interview_format = st.radio(
                            "**Interview Style**",
                            ["In-person", "Video Call", "Phone Interview"],
                            horizontal=True
                        )
                        
                        custom_message = st.text_area(
                            "**Special Notes**",
                            """Please bring a copy of your ID and any relevant certificates. *We can’t wait to meet you!*

If you need to reschedule, just reply to this email 24 hours in advance.""",
                            help="*Add a personal touch to wow them!*"
                        )
                        
                        with st.expander("📧 *Sneak Peek at Your Invite*"):
                            st.markdown(f"""
                            **Subject:** *Interview Invitation*
                            
                            **To:** [Candidate Name]
                            
                            Dear [Candidate Name],
                            
                            *Great news!* Your resume has been shortlisted for the role. We’re thrilled about your skills and can’t wait to chat!
                            
                            **Interview Details:**
                            - **Date:** {interview_date.strftime("%A, %B %d, %Y")}
                            - **Time:** {interview_time}
                            - **Format:** {interview_format}
                            - **Location:** {interview_location if interview_location else '*Virtual - details coming soon!*'}
                            
                            {custom_message}
                            
                            Please RSVP by replying to this email. If the time doesn’t work, let us know your availability!
                            
                            *Here’s to an exciting conversation ahead!*  
                            Best Regards,  
                            Recruitment Team
                            """)
                    else:
                        st.markdown("### 📝 *Craft a Status Update*")
                        rejection_type = st.radio(
                            "**Message Type**",
                            ["Rejection", "Still in Consideration", "Application Received"],
                            horizontal=True
                        )
                        
                        if rejection_type == "Rejection":
                            custom_message = st.text_area(
                                "**Your Message**",
                                """Your application blew us away, but we’re moving forward with candidates whose experience aligns more closely with this role.

*Thank you for applying—we’re rooting for your success!*""",
                                help="*Keep it kind and inspiring!*"
                            )
                            
                            with st.expander("📧 *Preview Your Update*"):
                                st.markdown(f"""
                                **Subject:** *Update on Your Application*
                                
                                **To:** [Candidate Name]
                                
                                Dear [Candidate Name],
                                
                                Thanks for applying—we loved seeing your passion!
                                
                                After a tough review, we’re not moving forward with your candidacy this time.
                                
                                {custom_message}
                                
                                *Keep shining—we know you’ll land something amazing!*  
                                Best Regards,  
                                Recruitment Team
                                """)
                        elif rejection_type == "Still in Consideration":
                            custom_message = st.text_area(
                                "**Your Message**",
                                """We’re still reviewing applications, and you’re *still in the running*! Final decisions are coming in the next two weeks.

*Hang tight—you’re on our radar!*""",
                                help="*Give them hope and excitement!*"
                            )
                            
                            with st.expander("📧 *Preview Your Update*"):
                                st.markdown(f"""
                                **Subject:** *Your Status*
                                
                                **To:** [Candidate Name]
                                
                                Dear [Candidate Name],
                                
                                Thanks for applying!
                                
                                {custom_message}
                                
                                No action needed now—we’ll reach out if we’re ready to move forward.  
                                Best Regards,  
                                Recruitment Team
                                """)
                        else:
                            custom_message = st.text_area(
                                "**Your Message**",
                                """*Welcome aboard the hiring journey!* We’ve received your application, and our team is diving into it now.

If you’re a match, we’ll be in touch for an interview soon!""",
                                help="*Make them feel valued from the start!*"
                            )
                            
                            with st.expander("📧 *Preview Your Update*"):
                                st.markdown(f"""
                                **Subject:** *Application Received*
                                
                                **To:** [Candidate Name]
                                
                                Dear [Candidate Name],
                                
                                *Big thanks* for applying!
                                
                                {custom_message}
                                
                                *We’re excited to have you in the mix!*  
                                Best Regards,  
                                Recruitment Team
                                """)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.info(f"*Ready to connect? You’ll reach {len(selected_candidates)} amazing candidates!*")
                    
                    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
                    if st.button("📨 *Send Emails Now*", use_container_width=True):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        success_count = 0
                        fail_count = 0
                        
                        for idx, candidate in enumerate(selected_candidates.itertuples()):
                            try:
                                if email_type == "Interview Invitation":
                                    subject = f"Interview Invitation"
                                    body = f"""Dear {candidate.Name},

*Great news!* Your resume has been shortlisted for the role. We’re thrilled about your skills and can’t wait to chat!

Interview Details:
- **Date:** {interview_date.strftime("%A, %B %d, %Y")}
- **Time:** {interview_time}
- **Format:** {interview_format}
- **Location:** {interview_location if interview_location else '*Virtual - details coming soon!*'}

{custom_message}

Please RSVP by replying to this email. If the time doesn’t work, let us know your availability!

*Here’s to an exciting conversation ahead!*  
Best Regards,
Recruitment Team"""
                                    attachment_path = candidate.Attachment if hasattr(candidate, 'Attachment') else None
                                else:
                                    if rejection_type == "Rejection":
                                        subject = f"Update on Your Application"
                                        body = f"""Dear {candidate.Name},

Thanks for applying—we loved seeing your passion!

After a tough review, we’re not moving forward with your candidacy this time.

{custom_message}

*Keep shining—we know you’ll land something amazing!*  
Best Regards,
Recruitment Team"""
                                    elif rejection_type == "Still in Consideration":
                                        subject = f"Your Status"
                                        body = f"""Dear {candidate.Name},

Thanks for applying!

{custom_message}

No action needed now—we’ll reach out if we’re ready to move forward.  
Best Regards,
Recruitment Team"""
                                    else:
                                        subject = f"Application Received"
                                        body = f"""Dear {candidate.Name},

*Big thanks* for applying!

{custom_message}

*We’re excited to have you in the mix!*  
Best Regards,
Recruitment Team"""
                                    attachment_path = None
                                
                                if send_email(
                                    st.session_state.sender_email,
                                    st.session_state.sender_password,
                                    candidate.Email,
                                    subject,
                                    body,
                                    attachment_path
                                ):
                                    success_count += 1
                                else:
                                    fail_count += 1
                                
                                time.sleep(1)
                                
                            except Exception as e:
                                st.error(f"Error sending email to {candidate.Name}: {e}")
                                fail_count += 1
                            
                            progress = (idx + 1) / len(selected_candidates)
                            progress_bar.progress(progress)
                            status_text.text(f"*Sending: {idx + 1}/{len(selected_candidates)}*")
                        
                        if success_count > 0:
                            if lottie_success:
                                st_lottie(lottie_success, height=120, key="email_success", speed=1.5)
                            st.success(f"✅ *Boom! {success_count} emails sent successfully!*")
                            st.session_state.active_tab = "💬 Interview Candidates"
                            st.rerun()
                        if fail_count > 0:
                            st.error(f"❌ *Oops! {fail_count} emails didn’t make it. Check the logs.*")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Email Settings Tab
    with tabs[1]:
        colored_header(label="Email Configuration", description="*Power up your outreach with a few clicks!*",
                      color_name="orange-70")
        
        st.info("""
        *Ready to connect with talent?* Set up your Gmail here to send dazzling emails with CyTibot.

        ℹ️ *Heads up:* Gmail needs an App Password for this—your regular password won’t cut it!
        """)
        
        st.markdown("""
        <div style="background-color: #e6f0fa; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 10px 0 rgba(0,0,0,0.1); margin-bottom: 1rem;">
        """, unsafe_allow_html=True)
        
        st.markdown("### *Unlock Gmail App Password Magic*")
        st.markdown("""
        1. Head to [Google Account Security](https://myaccount.google.com/security)  
        2. Turn on *2-Step Verification* if it’s not already on  
        3. Visit [App Passwords](https://myaccount.google.com/apppasswords)  
        4. Pick *Mail* and your device  
        5. Grab the *16-character code* and bring it here!
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            sender_email = st.text_input("**Your Gmail Address**",
                                       placeholder="your.email@gmail.com",
                                       value=st.session_state.get('sender_email', ''),
                                       help="*Your email HQ for candidate outreach!*")
            
            sender_password = st.text_input("**Gmail App Password**",
                                          help="Paste that 16-character code here!",
                                          type="password",
                                          placeholder="16-character app password")
        
        with col2:
            st.markdown("### *Test the Connection*")
            test_recipient = st.text_input("**Test Recipient Email**",
                                          value=sender_email if sender_email else "",
                                          placeholder="Who gets the test email?")
            
            if st.button("**Verify Connection**", use_container_width=True):
                if not sender_email or not sender_password:
                    st.error("*Fill in both fields to unlock email power!*")
                elif not test_recipient:
                    st.error("*Who’s getting the test email? Add a recipient!*")
                else:
                    with st.spinner("*Testing your email vibes...*"):
                        try:
                            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                                server.starttls()
                                server.login(sender_email, sender_password)
                                
                                msg = MIMEMultipart()
                                msg['From'] = sender_email
                                msg['To'] = test_recipient
                                msg['Subject'] = "CyTibot - Email Test"
                                
                                body = f"""Hello there,

*You’re in!* This is a test email from **CyTibot Resume Filtering**.

If this lands in your inbox, your email setup is *good to go* for connecting with talent!

Time: {datetime.datetime.now().strftime("%Y-%m-d %H:%M:%S")}

Cheers,  
The CyTibot Team"""
                                msg.attach(MIMEText(body, 'plain'))
                                
                                server.send_message(msg)
                            
                            st.success("✅ *Success! Your email’s ready to roll—test email sent!*")
                            
                            st.session_state.sender_email = sender_email
                            st.session_state.sender_password = sender_password
                            st.session_state.email_configured = True
                        except Exception as e:
                            st.error(f"❌ *Uh-oh! Email setup failed: {e}*")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        colored_header(label="Email Templates", description="*Customize your messages to dazzle candidates!*",
                      color_name="orange-30")
        
        template_type = st.selectbox(
            "**Pick a Template**",
            ["Interview Invitation", "Rejection Email", "Application Received", "Still in Consideration"]
        )
        
        template_content = ""
        if template_type == "Interview Invitation":
            template_content = """Dear {{candidate_name}},

*Great news!* Your resume has been shortlisted for the role. We’re thrilled about your skills and can’t wait to chat!

Interview Details:
- **Date:** {{interview_date}}
- **Time:** {{interview_time}}
- **Format:** {{interview_format}}
- **Location:** {{interview_location}}

{{custom_message}}

Please RSVP by replying to this email. If the time doesn’t work, let us know your availability!

*Here’s to an exciting conversation ahead!*  
Best Regards,  
Recruitment Team"""
        elif template_type == "Rejection Email":
            template_content = """Dear {{candidate_name}},

Thanks for applying—we loved seeing your passion!

After a tough review, we’re not moving forward with your candidacy this time.

{{custom_message}}

*Keep shining—we know you’ll land something amazing!*  
Best Regards,  
Recruitment Team"""
        elif template_type == "Application Received":
            template_content = """Dear {{candidate_name}},

*Big thanks* for applying!

{{custom_message}}

*We’re excited to have you in the mix!*  
Best Regards,  
Recruitment Team"""
        elif template_type == "Still in Consideration":
            template_content = """Dear {{candidate_name}},

Thanks for applying!

{{custom_message}}

No action needed now—we’ll reach out if we’re ready to move forward.  
Best Regards,  
Recruitment Team"""
        
        st.text_area("**Email Template**", value=template_content, height=400)
        
        st.markdown("""
        **Template Superpowers:**
        - `{{candidate_name}}` - *Their name, front and center*
        - `{{interview_date}}` - *When the spotlight hits*
        - `{{interview_time}}` - *The perfect time slot*
        - `{{interview_format}}` - *In-person, video, or phone vibes*
        - `{{interview_location}}` - *Where it all goes down*
        - `{{custom_message}}` - *Your special flair*
        """)

    # Interview Candidates Tab
    with tabs[2]:
        colored_header(label="Interview Candidates", description="*Conduct skill-based interviews with ease!*",
                      color_name="orange-70")
        
        if 'filtered_results' not in st.session_state or st.session_state.filtered_results.empty:
            st.warning("⚠️ *No candidates available for interview. Please filter resumes first!*")
        else:
            selected_candidates = st.session_state.filtered_results[st.session_state.filtered_results["Send Email"] == True]
            
            if selected_candidates.empty:
                st.info("*No candidates have been emailed yet. Send emails to start interviewing!*")
            else:
                st.markdown("### *Select a Candidate to Interview*")
                candidate_names = selected_candidates["Name"].tolist()
                selected_candidate = st.selectbox("**Choose a Candidate**", candidate_names, key="candidate_select")
                
                if selected_candidate:
                    candidate_data = selected_candidates[selected_candidates["Name"] == selected_candidate].iloc[0]
                    st.session_state.current_candidate = selected_candidate
                    st.session_state.candidate_skills = candidate_data["Skills"]
                    
                    chat_interface(selected_candidate, candidate_data["Skills"])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"*Oops! Something went wrong: {e}*")
        st.info("*Check your inputs and let’s try again!*")