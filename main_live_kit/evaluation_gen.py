import google.generativeai as genai
import json
import re
try:
    from resume_jd_analyser.ai_utils import get_gemini_fast_model, SAFETY_SETTINGS
except ImportError:
    
    import sys 
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from resume_jd_analyser.ai_utils import get_gemini_fast_model, SAFETY_SETTINGS

model = get_gemini_fast_model()

def evaluate_candidate(transcript_text, jd_text, resume_text):
    """
    Evaluates the candidate based on the interview transcript, JD, and Resume.
    Returns a JSON string with the evaluation results.
    """
    system_prompt = f"""
    You are an expert Senior Technical Recruiter and Hiring Manager at NEWEL TECHNOLOGIES.
    Your task is to strictly evaluate the candidate's interview performance based on the provided transcript, Job Description, and Resume.

    INPUT DATA:
    1. JOB DESCRIPTION (JD): The standard for required skills and knowledge.
    2. RESUME: The candidate's claimed experience.
    3. TRANSCRIPT: The actual Q&A from the interview.

    EVALUATION CRITERIA:
    - Relevance: Did the answer directly address the question?
    - Technical Accuracy: Was the technical detail correct and sufficient for the role?
    - Communication: Was the answer clear, concise, and professional?
    - Consistency: Did the answers align with the Resume claims?

    OUTPUT FORMAT:
    You must return the result in strictly VALID JSON format with no additional text or markdown formatting.
    Structure:
    {{
        "candidate_name": "Name from Resume",
        "overall_score": (Integer 1-10),
        "technical_score": (Integer 1-10),
        "communication_score": (Integer 1-10),
        "recommendation": "Strong Hire" | "Hire" | "Weak Hire" | "Reject",
        "summary": "A brief executive summary of the performance (max 3 sentences).",
        "detailed_feedback": [
            {{
                "question": "The question asked",
                "candidate_answer_summary": "Summary of what they said",
                "score": (1-10),
                "feedback": "Specific technical feedback on what was good or missing."
            }},
            ... (repeat for all substantive questions)
        ]
    }}

    CONTEXT:
    
    --- JOB DESCRIPTION ---
    {jd_text}
    
    --- RESUME ---
    {resume_text}
    
    --- INTERVIEW TRANSCRIPT ---
    {transcript_text}
    
    """

    try:
        response = model.generate_content(system_prompt, safety_settings=SAFETY_SETTINGS)
        
        
        text_response = response.text
        if "```json" in text_response:
            text_response = text_response.replace("```json", "").replace("```", "")
        
        return text_response.strip()

    except Exception as e:
        return json.dumps({
            "error": f"Evaluation generation failed: {str(e)}",
            "overall_score": 0,
            "recommendation": "Error"
        })
    