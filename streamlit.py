import os
import re
import json
import asyncio
import streamlit as st
import pdfplumber
import google.generativeai as genai
from urllib.parse import quote
import pandas as pd

# Directory for storing resumes
UPLOAD_DIRECTORY = "uploaded_resumes"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Google Gemini API Keys with Rotation
API_KEYS = [
    "AIzaSyAYIIwHicFzIv2gYRUvk2pfEsnqVje9TfA",
    "AIzaSyAznPx4tiDhm5hnt1w1qQSoNjxEQgV4KUQ",
    "AIzaSyDmbj626LuMQwAJcmaJZwzdYfOdR_U96KI",
    "AIzaSyBAyUq6fntEPR4DN7WWWw0KlyTOdrhRUac"
]
current_api_index = 0

def set_api_key():
    global current_api_index
    genai.configure(api_key=API_KEYS[current_api_index])

def rotate_api_key():
    global current_api_index
    current_api_index = (current_api_index + 1) % len(API_KEYS)
    set_api_key()

set_api_key()

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Improved contact info extraction
def extract_contact_info_and_name(resume_text):
    email_pattern = r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+'
    
    # More generalized phone pattern to catch international formats
    phone_pattern = re.compile(r"""
        (?:
            (?:\+\d{1,3}[\s\-\.]?)?                # Optional country code with +
            (?:\(?\d{1,4}\)?[\s\-\.]?)?           # Optional area code, possibly in parentheses
            \d{3}[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}  # Main number groups
            |
            \d{10,12}                             # Simple 10-12 digit number
        )
    """, re.VERBOSE)

    emails = re.findall(email_pattern, resume_text)
    
    # Find all potential phone numbers
    phone_candidates = re.findall(phone_pattern, resume_text)
    
    # Clean up found phone numbers and keep valid ones
    phones = []
    for p in phone_candidates:
        # Clean the phone number of spaces, dashes, dots, parentheses
        cleaned = re.sub(r'[\s\-\.\(\)]', '', p)
        # Keep only if it's a reasonable length for a phone number (7+ digits)
        if len(cleaned) >= 7:
            phones.append(p)
    
    # Fallback: Check for "Phone:", "Mobile:", "Contact:", "Tel:" prefixes
    if not phones:
        phone_prefix_pattern = re.compile(r'(?:Phone|Mobile|Contact|Tel|Cell)[:\s]*([+0-9\s\-\.\(\)]+)')
        phone_matches = phone_prefix_pattern.findall(resume_text)
        for p in phone_matches:
            cleaned = re.sub(r'[\s\-\.\(\)]', '', p)
            if len(cleaned) >= 7:
                phones.append(p)
    
    email = emails[0] if emails else "N/A"
    phone = phones[0] if phones else "N/A"

    # Extract candidate name from the top lines (first 5 lines usually contain name)
    lines = resume_text.split("\n")
    candidate_name = "N/A"
    for line in lines[:5]:
        words = line.strip().split()
        if len(words) >= 2 and all(word.isalpha() for word in words):
            candidate_name = line.strip()
            break

    return candidate_name, email, phone

async def analyze_resume(resume_text, filename, job_description, min_experience, min_ats_score):
    prompt = f"""
    You are an ATS system evaluating resumes against job descriptions.

    JOB DESCRIPTION:
    {job_description}

    RESUME CONTENT:
    {resume_text}

    Please return a structured JSON object with:
    {{
        "ats_score": (0 to 100),
        "meets_requirements": (true/false),
        "match_details": "Brief explanation highlighting matches or mismatches",
        "extracted_skills": "Comma-separated list of relevant skills found in the resume"
    }}

    Only return valid JSON.
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
                raise ValueError(f"Invalid JSON response from Gemini: {response_text}")

            return {
                "is_match": result["meets_requirements"] and result["ats_score"] >= min_ats_score,
                "ats_score": result["ats_score"],
                "match_details": result["match_details"],
                "extracted_skills": result["extracted_skills"]
            }
        except Exception as e:
            if "429" in str(e):
                rotate_api_key()
            else:
                st.error(f"Gemini Error: {e}")
                return None

# Streamlit UI
st.title("📄 Resume Filtering Bot")
st.subheader("Upload resumes and filter them based on your Job Description using Google Gemini AI.")

uploaded_files = st.file_uploader("Upload up to 100 resumes (PDF only)", type=["pdf"], accept_multiple_files=True)

if uploaded_files and len(uploaded_files) > 100:
    st.error("You can upload a maximum of 100 resumes at once.")
    uploaded_files = uploaded_files[:100]

job_description = st.text_area("Paste Job Description (JD)", height=150)
min_experience = st.number_input("Minimum Experience (years)", min_value=0, value=0)
min_ats_score = st.slider("Minimum ATS Score", 0, 100, 70)

if st.button("Start Filtering Process"):
    if not uploaded_files or not job_description:
        st.error("Please upload resumes and paste a Job Description.")
    else:
        file_paths = [os.path.join(UPLOAD_DIRECTORY, file.name) for file in uploaded_files]
        for file, path in zip(uploaded_files, file_paths):
            with open(path, "wb") as f:
                f.write(file.read())

        st.info("🔍 Processing resumes...")
        matching_resumes = []
        progress_bar = st.progress(0)

        for idx, file_path in enumerate(file_paths):
            resume_text = extract_text_from_pdf(file_path)
            candidate_name, email, phone = extract_contact_info_and_name(resume_text)

            analysis = asyncio.run(analyze_resume(
                resume_text,
                os.path.basename(file_path),
                job_description,
                min_experience,
                min_ats_score
            ))

            if analysis and analysis["is_match"]:
                matching_resumes.append({
                    "Candidate Name": candidate_name,
                    "ATS Score": analysis["ats_score"],
                    "Skills": analysis["extracted_skills"].replace(", ", "\n"),  # Display skills line-by-line
                    "Email": email,
                    "Phone": phone,
                    "View": f'<a href="{file_path}" target="_blank">View Resume</a>'
                })

            progress_bar.progress((idx + 1) / len(file_paths))

        if matching_resumes:
            st.success(f"✅ Process completed! {len(matching_resumes)} resumes matched.")
            df = pd.DataFrame(matching_resumes)

            # Render table with clickable links & formatted skills
            st.markdown(
                df.to_html(index=False, escape=False).replace("\\n", "<br>"),
                unsafe_allow_html=True
            )
        else:
            st.warning("No resumes matched the criteria.")
