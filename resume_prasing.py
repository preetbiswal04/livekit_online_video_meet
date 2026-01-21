import google.generativeai as genai
import os
import json
import re

genai.configure(api_key=os.getenv("gemini_api_key"))

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel("gemini-2.0-flash")

def prase_resume(resume_text):
    prompt = f"""
    Extract the following information from the resume:
    -Name
    -Phone Number
    -Email
    -Education
    -Skills
    -Experience
    
    Return strict in JSON format

    {resume_text}
    """
    response = model.generate_content(prompt, safety_settings=safety_settings)
    
    # Check if blocked
    if not response.candidates or not response.candidates[0].content.parts:
        return {"error": "Content blocked by safety filters"}

    # Cleaning the response text to extract only JSON
    text = response.text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
    
    try:
        return json.loads(text)
    except Exception:
        return {"error": "Failed to parse JSON", "raw": response.text}