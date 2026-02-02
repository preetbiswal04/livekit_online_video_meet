import google.generativeai as genai
import os
import json
import re
from .ai_utils import get_gemini_fast_model, SAFETY_SETTINGS

model = get_gemini_fast_model()



def jd_prase(jd_text):
    prompt = f"""
    Extract the following information from the job description:
    - job_title (or role)
    - company_name
    - required_skills
    - required_experience
    - required_education

    Return strict in JSON format with keys: "job_role", "company_name", "skills", "experience", "education".
    
    {jd_text}
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
