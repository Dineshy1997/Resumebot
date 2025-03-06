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

# Initialize API key
set_api_key()

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file"""
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
    """Generate a download link for a PDF file"""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        href = f'<a href="data:application/pdf;base64,{base64_pdf}" download="{file_name}" target="_blank">View Resume</a>'
        return href
    except Exception as e:
        st.error(f"Error creating download link: {e}")
        return "Link Error"

def extract_contact_info_and_name(resume_text):
    """
    Enhanced function to extract candidate name, email and phone from resume text.
    Uses multiple strategies to increase the chance of finding the correct name.
    """
    if not resume_text:
        return "N/A", "N/A", "N/A"
        
    # Email extraction pattern
    email_pattern = r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+'
    emails = re.findall(email_pattern, resume_text)
    
    # Phone extraction pattern (enhanced)
    phone_pattern = re.compile(r"""
        (?:
            (?:\+\d{1,3}[\s\-\.]?)?                # Optional country code with +
            (?:\(?\d{1,4}\)?[\s\-\.]?)?           # Optional area code, possibly in parentheses
            \d{3}[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}  # Main number groups
            |
            \d{10,12}                             # Simple 10-12 digit number
        )
    """, re.VERBOSE)
    
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
    
    # Fallback for phone: Check for "Phone:", "Mobile:", "Contact:", "Tel:" prefixes
    if not phones:
        phone_prefix_pattern = re.compile(r'(?:Phone|Mobile|Contact|Tel|Cell)[:\s]*([+0-9\s\-\.\(\)]+)')
        phone_matches = phone_prefix_pattern.findall(resume_text)
        for p in phone_matches:
            cleaned = re.sub(r'[\s\-\.\(\)]', '', p)
            if len(cleaned) >= 7:
                phones.append(p)
    
    email = emails[0] if emails else "N/A"
    phone = phones[0] if phones else "N/A"

    # IMPROVED NAME EXTRACTION - MULTIPLE STRATEGIES
    candidate_name = "N/A"
    
    # Strategy 1: Check for name patterns at the beginning of the resume
    lines = resume_text.strip().split("\n")
    first_non_empty_lines = [line.strip() for line in lines[:10] if line.strip()]
    
    # Common name patterns (2-3 words, capitalized, no numbers or special chars)
    for line in first_non_empty_lines:
        # Skip lines that are too long (likely not a name)
        if len(line) > 50:
            continue
            
        # Skip lines that are just single words unless all caps (could be logo or header)
        words = line.split()
        if len(words) == 1 and not line.isupper():
            continue
            
        # Check for a name-like pattern: 2-3 capitalized words
        words = line.strip().split()
        if 1 <= len(words) <= 4:
            # Check if words look like a name (starts with uppercase, only alphabetic)
            potential_name = True
            for word in words:
                # Skip words that are single letters (middle initials)
                if len(word) == 1:
                    continue
                # Check if word starts with uppercase and doesn't contain digits or special chars
                if not (word[0].isupper() and all(c.isalpha() or c in "-'" for c in word)):
                    potential_name = False
                    break
            
            if potential_name:
                candidate_name = line.strip()
                break
    
    # Strategy 2: Look for specific name indicators
    if candidate_name == "N/A":
        name_indicators = [
            r'Name\s*:\s*([A-Z][a-zA-Z\s\.\-\']{2,30})',
            r'^([A-Z][a-zA-Z\.\-\'\s]{2,30})$',  # Line with just a name
            r'([A-Z][a-zA-Z\.\-\']{1,25}\s+[A-Z][a-zA-Z\.\-\']{1,25}(?:\s+[A-Z][a-zA-Z\.\-\']{1,25})?)'  # First Last pattern
        ]
        
        for pattern in name_indicators:
            matches = re.findall(pattern, resume_text, re.MULTILINE)
            if matches:
                # Get the first match that doesn't look like an address or title
                for match in matches:
                    if len(match.split()) <= 4 and not any(word.lower() in match.lower() for word in ['street', 'avenue', 'road', 'linkedin', 'github', 'profile']):
                        candidate_name = match.strip()
                        break
                if candidate_name != "N/A":
                    break
    
    # Strategy 3: Try to extract name from email address
    if candidate_name == "N/A" and email != "N/A":
        # Extract username part from email
        username = email.split('@')[0]
        # Try to convert username to a name format
        # Replace dots, underscores, numbers with spaces and capitalize
        username = re.sub(r'[._0-9]', ' ', username).strip()
        if username and len(username) > 3:  # Reasonable name length
            name_parts = username.split()
            name_parts = [part.capitalize() for part in name_parts]
            if len(name_parts) >= 1:
                candidate_name = ' '.join(name_parts)
    
    # Strategy 4: Look for LinkedIn profile URLs
    if candidate_name == "N/A":
        linkedin_pattern = r'linkedin\.com\/in\/([a-zA-Z0-9\-]+)'
        linkedin_matches = re.findall(linkedin_pattern, resume_text)
        if linkedin_matches:
            # Convert LinkedIn username to potential name
            username = linkedin_matches[0].replace('-', ' ')
            name_parts = username.split()
            name_parts = [part.capitalize() for part in name_parts]
            if len(name_parts) >= 1:
                candidate_name = ' '.join(name_parts)

    return candidate_name, email, phone

async def analyze_resume(resume_text, filename, job_description, min_experience, min_ats_score):
    prompt = f"""
    You are an ATS system evaluating resumes against job descriptions.

    JOB DESCRIPTION:
    {job_description}

    RESUME CONTENT:
    {resume_text}

    INSTRUCTIONS:
    Analyze the resume against the job description.
    You MUST return a valid JSON object with exactly the following structure and nothing else:
    {{
        "ats_score": (number between 0 to 100),
        "meets_requirements": (true/false),
        "match_details": "Brief explanation highlighting matches or mismatches",
        "extracted_skills": "Comma-separated list of relevant skills found in the resume",
        "total_years_experience": (integer representing total years of work experience, rounded to nearest whole number),
        "experience_details": "Brief summary of relevant experience"
    }}
    
    Do not include any explanations, conversations, or additional text outside the JSON object.
    """

    while True:
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Try to parse the whole response as JSON first
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                json_text = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_text:
                    result = json.loads(json_text.group())
                else:
                    # If we can't find JSON, retry with a more forceful prompt
                    rotate_api_key()
                    prompt += "\n\nIMPORTANT: You MUST return ONLY a valid JSON object with no additional text."
                    continue

            # Validate that the JSON has all required fields
            required_fields = ["ats_score", "meets_requirements", "match_details", "extracted_skills", 
                              "total_years_experience", "experience_details"]
            if not all(field in result for field in required_fields):
                rotate_api_key()
                prompt += "\n\nIMPORTANT: The JSON response is missing required fields. Include ALL fields as specified."
                continue
                
            # Ensure total_years_experience is an integer
            if not isinstance(result["total_years_experience"], int):
                try:
                    # Round to nearest integer if it's a float
                    result["total_years_experience"] = round(float(result["total_years_experience"]))
                except (ValueError, TypeError):
                    # If conversion fails, default to 0
                    result["total_years_experience"] = 0

            # Check if the candidate meets the minimum experience requirement
            experience_requirement_met = result["total_years_experience"] >= min_experience
            
            return {
                "is_match": result["meets_requirements"] and result["ats_score"] >= min_ats_score and experience_requirement_met,
                "ats_score": result["ats_score"],
                "match_details": result["match_details"],
                "extracted_skills": result["extracted_skills"],
                "total_years_experience": result["total_years_experience"],
                "experience_details": result["experience_details"]
            }
        except Exception as e:
            if "429" in str(e):
                rotate_api_key()
            else:
                st.error(f"Gemini Error: {e}")
                return None

# Streamlit UI
def main():
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
            processed_files = {}  # Dictionary to track which files match
            progress_bar = st.progress(0)

            for idx, file_path in enumerate(file_paths):
                try:
                    resume_text = extract_text_from_pdf(file_path)
                    candidate_name, email, phone = extract_contact_info_and_name(resume_text)

                    analysis = asyncio.run(analyze_resume(
                        resume_text,
                        os.path.basename(file_path),
                        job_description,
                        min_experience,
                        min_ats_score
                    ))

                    file_name = os.path.basename(file_path)
                    processed_files[file_name] = analysis and analysis["is_match"]

                    if analysis and analysis["is_match"]:
                        # Generate download link for the PDF
                        download_link = get_pdf_download_link(file_path, file_name)
                        
                        # Create result dictionary with experience column positioned after candidate name
                        # Display experience as a whole number
                        result_dict = {
                            "Candidate Name": candidate_name,
                            "Experience": f"{analysis['total_years_experience']} years",
                            "ATS Score": analysis["ats_score"],
                            "Skills": analysis["extracted_skills"].replace(", ", "\n"),  # Display skills line-by-line
                            "Email": email,
                            "Phone": phone,
                            "View": download_link
                        }
                        
                        matching_resumes.append(result_dict)
                except Exception as e:
                    st.error(f"Error processing {os.path.basename(file_path)}: {e}")
                
                progress_bar.progress((idx + 1) / len(file_paths))

            if matching_resumes:
                st.success(f"✅ Process completed! {len(matching_resumes)} resumes matched.")
                
                # Create DataFrame with columns in desired order
                df = pd.DataFrame(matching_resumes)
                
                # Ensure column order (for better table structure)
                column_order = [
                    "Candidate Name", 
                    "Experience",
                    "ATS Score", 
                    "Skills", 
                    "Email", 
                    "Phone", 
                    "View"
                ]
                # Filter to only include columns that exist in the DataFrame
                column_order = [col for col in column_order if col in df.columns]
                df = df[column_order]

                # Render table with clickable links & formatted skills
                st.markdown(
                    df.to_html(index=False, escape=False).replace("\\n", "<br>"),
                    unsafe_allow_html=True
                )
                
                # Add summary of results
                st.subheader("Processing Summary")
                st.write(f"Total Resumes: {len(file_paths)}")
                st.write(f"Matching Resumes: {len(matching_resumes)}")
                st.write(f"Rejected Resumes: {len(file_paths) - len(matching_resumes)}")
                
            else:
                st.warning("No resumes matched the criteria.")

if __name__ == "__main__":
    main()
