import os
import re
import json
import base64
import asyncio
import streamlit as st
import pdfplumber
import google.generativeai as genai
import pandas as pd
from urllib.parse import quote

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
    st.warning(f"🔄 Switched to API Key {current_api_index + 1}")

set_api_key()

# Extract text from PDF using pdfplumber
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Create downloadable link for resume
def get_pdf_download_link(file_path, file_name):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    return f'<a href="data:application/pdf;base64,{base64_pdf}" download="{file_name}" target="_blank">View Resume</a>'

# Extract contact information (email, phone) using regex
def extract_contact_info(resume_text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = re.compile(r'(\+?\d[\d\s\-().]{8,}\d)')

    emails = re.findall(email_pattern, resume_text)
    phones = re.findall(phone_pattern, resume_text)

    email = emails[0] if emails else "N/A"
    phone = phones[0] if phones else "N/A"
    return email, phone

# Use Gemini to analyze resume and extract details including candidate name
async def analyze_resume(resume_text, job_description, min_experience, min_ats_score):
    prompt = f"""
    You are an ATS system evaluating resumes against job descriptions.

    JOB DESCRIPTION:
    {job_description}

    RESUME CONTENT:
    {resume_text}

    INSTRUCTIONS:
    Analyze the resume against the job description.
    Return a JSON object with this structure:
    {{
        "candidate_name": "Full candidate name extracted from resume",
        "ats_score": (number between 0 and 100),
        "meets_requirements": (true/false),
        "match_details": "Brief explanation highlighting matches or mismatches",
        "extracted_skills": "Comma-separated list of relevant skills found in the resume",
        "total_years_experience": (integer rounded to nearest whole number),
        "experience_details": "Brief summary of relevant experience"
    }}
    Only return the JSON object, no explanations or additional text.
    """

    while True:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Attempt to parse response directly as JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                json_text = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_text:
                    result = json.loads(json_text.group())
                else:
                    rotate_api_key()
                    continue

            required_fields = [
                "candidate_name", "ats_score", "meets_requirements",
                "match_details", "extracted_skills",
                "total_years_experience", "experience_details"
            ]
            if not all(field in result for field in required_fields):
                rotate_api_key()
                continue

            if not isinstance(result["total_years_experience"], int):
                result["total_years_experience"] = round(float(result.get("total_years_experience", 0)))

            experience_requirement_met = result["total_years_experience"] >= min_experience
            is_match = (
                result["meets_requirements"] and 
                result["ats_score"] >= min_ats_score and 
                experience_requirement_met
            )

            result["is_match"] = is_match
            return result

        except Exception as e:
            if "429" in str(e):
                rotate_api_key()
            else:
                st.error(f"Gemini Error: {e}")
                return None

# Streamlit UI
st.title("📄 Resume Filtering Bot")
st.subheader("Upload resumes and filter them based on your Job Description.")

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
            try:
                resume_text = extract_text_from_pdf(file_path)
                email, phone = extract_contact_info(resume_text)

                analysis = asyncio.run(analyze_resume(
                    resume_text, job_description, min_experience, min_ats_score
                ))

                if analysis and analysis["is_match"]:
                    matching_resumes.append({
                        "Candidate Name": analysis["candidate_name"],
                        "Experience": f'{analysis["total_years_experience"]} years',
                        "ATS Score": analysis["ats_score"],
                        "Skills": analysis["extracted_skills"].replace(", ", "<br>"),
                        "Email": email,
                        "Phone": phone,
                        "View": get_pdf_download_link(file_path, os.path.basename(file_path))
                    })
            except Exception as e:
                st.error(f"Error processing {os.path.basename(file_path)}: {e}")

            progress_bar.progress((idx + 1) / len(file_paths))

        if matching_resumes:
            st.success(f"✅ Process completed! {len(matching_resumes)} resumes matched the criteria.")

            df = pd.DataFrame(matching_resumes)

            column_order = [
                "Candidate Name", "Experience", "ATS Score",
                "Skills", "Email", "Phone", "View"
            ]
            df = df[column_order]

            # Display results table with clickable view links and skills line by line
            st.markdown(
                df.to_html(index=False, escape=False).replace("\\n", "<br>"),
                unsafe_allow_html=True
            )
            st.write(f"Total Resumes Processed: {len(file_paths)}")
            st.write(f"Matching Resumes: {len(matching_resumes)}")
        else:
            st.warning("No resumes matched the criteria.")
