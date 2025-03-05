import os
import re
import json
import asyncio
import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
from urllib.parse import quote
import pandas as pd

# Directory for storing resumes
UPLOAD_DIRECTORY = "uploaded_resumes"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Google Gemini API Keys with Rotation
API_KEYS = [
    "AIzaSyA77rBG8EaTlCzwwf_SCgAOVeQS11kbi8s",
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

# Initialize the first API key
set_api_key()

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    return "".join(page.extract_text() or "" for page in reader.pages)

def extract_contact_info(resume_text):
    email_pattern = r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+'
    phone_pattern = r'\b\d{10}\b'

    emails = re.findall(email_pattern, resume_text)
    phones = re.findall(phone_pattern, resume_text)

    email = emails[0] if emails else "N/A"
    phone = phones[0] if phones else "N/A"

    return email, phone

async def extract_candidate_name_with_gemini(resume_text):
    prompt = f"""
    Extract only the **candidate's full name** from the following resume text.

    Resume Text:
    {resume_text}

    Please only return the full name (first name and last name) in a single line. 
    If the name cannot be found, return "Unknown".
    """

    while True:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            name = response.text.strip()

            if len(name.split()) >= 2 and len(name) < 50:
                return name
            else:
                return "Unknown"
        except Exception as e:
            if "429" in str(e):  # Quota exhausted error handling - silent retry
                rotate_api_key()
            else:
                return "Unknown"

async def analyze_resume(resume_text, filename, job_description, min_experience, min_ats_score):
    prompt = f"""
    You are an advanced ATS system designed to evaluate resumes against job descriptions.

    JOB DESCRIPTION:
    {job_description}

    RESUME CONTENT:
    {resume_text}

    REQUIREMENTS:
    - Minimum Experience Required: {min_experience} years
    - Desired Skills & Qualifications: As described in the job description.

    Please analyze this resume and return a structured JSON response with the following fields:
    {{
      "ats_score": (number from 0 to 100),
      "meets_requirements": (true/false),
      "match_details": "Brief explanation highlighting key matches or mismatches",
      "extracted_skills": "Comma-separated list of relevant skills found in the resume"
    }}

    Only return the JSON object. No extra text.
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

            ats_score = result.get("ats_score", 0)
            meets_requirements = result.get("meets_requirements", False)
            match_details = result.get("match_details", "No explanation provided")
            extracted_skills = result.get("extracted_skills", "N/A")

            is_match = meets_requirements and ats_score >= min_ats_score

            return {
                "is_match": is_match,
                "ats_score": ats_score,
                "match_details": match_details,
                "extracted_skills": extracted_skills
            }
        except Exception as e:
            if "429" in str(e):  # Quota exhausted - silently rotate key
                rotate_api_key()
            else:
                st.error(f"Unexpected Error during resume analysis: {e}")
                return None

# Streamlit UI
st.title("📄 Resume Filtering Bot")
st.subheader("Upload resumes and filter them based on your Job Description using Google Gemini AI.")

uploaded_files = st.file_uploader("Upload up to 100 resumes (PDF only)", type=["pdf"], accept_multiple_files=True)

if uploaded_files and len(uploaded_files) > 100:
    st.error("You can upload a maximum of 100 resumes at once.")
    uploaded_files = uploaded_files[:100]  # Truncate to 100 resumes if more were uploaded

job_description = st.text_area("Paste Job Description (JD) here", height=150)

min_experience = st.number_input("Minimum Required Experience (in years)", min_value=0, value=0)
min_ats_score = st.slider("Minimum ATS Score", 0, 100, 70)

if st.button("Start Filtering Process"):
    if not uploaded_files or not job_description:
        st.error("Please upload resumes and provide a Job Description.")
    else:
        file_paths = []
        for file in uploaded_files:
            file_path = os.path.join(UPLOAD_DIRECTORY, file.name)
            with open(file_path, "wb") as f:
                f.write(file.read())
            file_paths.append(file_path)

        st.info("🔍 Processing resumes...")
        matching_resumes = []
        progress_bar = st.progress(0)

        for idx, file_path in enumerate(file_paths):
            resume_text = extract_text_from_pdf(file_path)
            email, phone = extract_contact_info(resume_text)

            candidate_name = asyncio.run(extract_candidate_name_with_gemini(resume_text))

            analysis = asyncio.run(
                analyze_resume(
                    resume_text,
                    os.path.basename(file_path),
                    job_description,
                    min_experience,
                    min_ats_score
                )
            )

            if analysis and analysis["is_match"]:
                matching_resumes.append({
                    "candidate_name": candidate_name,
                    "ats_score": analysis["ats_score"],
                    "match_details": analysis["match_details"],
                    "skills": analysis["extracted_skills"],
                    "email": email,
                    "phone": phone,
                    "download_link": f"{UPLOAD_DIRECTORY}/{quote(os.path.basename(file_path))}"
                })

            progress_bar.progress((idx + 1) / len(file_paths))

        matching_resumes = sorted(matching_resumes, key=lambda x: x["ats_score"], reverse=True)

        if matching_resumes:
            st.success(f"✅ Process completed! {len(matching_resumes)} resumes matched the criteria.")
            df = pd.DataFrame(matching_resumes)

            df["View"] = df["download_link"].apply(lambda x: f'<a href="{x}" target="_blank">View Resume</a>')

            st.write("### 📝 Filtered Resumes:")

            st.markdown(
                df[["candidate_name", "ats_score", "skills", "email", "phone", "View"]]
                .rename(columns={
                    "candidate_name": "Candidate Name",
                    "ats_score": "ATS Score",
                    "skills": "Skills",
                    "email": "Email",
                    "phone": "Phone",
                    "View": "View"
                })
                .to_html(index=False, escape=False),
                unsafe_allow_html=True
            )
        else:
            st.warning("No resumes matched the criteria.")
