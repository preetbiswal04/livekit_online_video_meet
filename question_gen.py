import google.generativeai as genai
import os 

genai.configure(api_key=os.getenv("gemini_api_key"))

# Safety settings to prevent technical content from being blocked
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel("gemini-2.0-flash")

def generate_questions(resume_json, jd_json):
    prompt = f"""
    You are an expert technical interviewer.
Your task is to generate interview questions strictly and only based on the provided Job Description.

Rules:
- Ask questions only from skills, tools, technologies, responsibilities, and qualifications explicitly mentioned in the Job Description.
- Do NOT ask generic, behavioral, HR, or personality questions.
- Do NOT ask questions outside the Job Description and Resume (no extra technologies, frameworks, or concepts).
- If a skill is mentioned briefly, ask basic and easy questions about it.
- If a skill is emphasized or repeated, ask in-depth technical questions.

The questions should go like this :
-There should be total 10 questions.
-The start of interview should be by introduction of role and comapny and ask candidate introduces them self.
-Then ask 3 questions from each project mentioned in resume.
-Then ask 3 question from tools and skills mentioned in resume.
-Then ask 2 technical questions from job description.
-Then ask 2 questions from experience mentioned in resume.

Return only questions in JSON format.


    
    
    Resume information:
    {resume_json}
    
    Job description information:
    {jd_json}
    """
    response = model.generate_content(prompt, safety_settings=safety_settings)
    
    # Robust check for blocked content
    if not response.candidates or not response.candidates[0].content.parts:
        return "Error: The response was blocked by Gemini safety filters or failed to generate. Try rephrasing your input."
        
    return response.text
