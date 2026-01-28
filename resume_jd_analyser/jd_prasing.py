import google.generativeai as genai
import os
import json
import re
from .ai_utils import get_gemini_fast_model, SAFETY_SETTINGS

model = get_gemini_fast_model()



def jd_prase(jd_text):
    prompt = f"""
    Extract the following information from the resume:
    -job title
    -job role
    -Required skills
    -Required experience
    -Required education

    Return strict in JSON format

    {jd_text}
    """
    response = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
    
    # Check if blocked
    if not response.candidates or not response.candidates[0].content.parts:
        return {"error": "Content blocked by safety filters"}

    text = response.text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
    
    try:
        return json.loads(text)
    except Exception:
        return {"error": "Failed to parse JSON", "raw": response.text}
