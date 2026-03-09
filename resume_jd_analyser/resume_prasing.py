import os
import json
import re
from .ai_utils_2 import get_gemini_fast_model, SAFETY_SETTINGS
from dotenv import load_dotenv

model = get_gemini_fast_model()



def prase_resume(resume_text):
    prompt = f"""
    You are a professional resume parser. Extract the following information from the provided resume text.
    
    FIELDS TO EXTRACT:
    - "Name": The candidate's FULL NAME (e.g., "John Doe"). Look at the very top of the resume. If you cannot find a clear full name, look for names in headers or contact sections.
    - "Phone Number"
    - "Email"
    - "Education"
    - "Skills"
    - "Experience"
    
    OUTPUT FORMAT:
    Return the result in STRICT JSON format only. Do not include any other text.
    
    RESUME TEXT:
    {resume_text}
    """
    

    response = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
    if not response.candidates or not response.candidates[0].content.parts:
        return {"error": "Content blocked by safety settings"}
    text = response.text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match :
        text = json_match.group(0)
    try:
        return json.loads(text)
    except Exception as e:
        return {"error": "Failed to parse JSON", "raw": response.text}
