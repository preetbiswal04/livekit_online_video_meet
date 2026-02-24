import json
import re
try:
    from resume_jd_analyser.ai_utils_2 import get_gemini_fast_model, SAFETY_SETTINGS
except ImportError:
    import sys 
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from resume_jd_analyser.ai_utils_2 import get_gemini_fast_model, SAFETY_SETTINGS

model = get_gemini_fast_model()

def evaluate_candidate(transcript_text, jd_text, resume_text):
    """
    Evaluates the candidate based on the interview transcript, JD, and Resume.
    Returns a JSON string with the evaluation results.
    """
    system_prompt =f"""
You are an expert Senior Technical Recruiter and Hiring Manager at NEWEL TECHNOLOGIES.
Your task is to strictly and objectively evaluate the candidate's interview performance based on the provided Job Description, Resume, and Interview Transcript.

You must behave like a real hiring manager making a final hiring decision.

INPUT DATA:
1. JOB DESCRIPTION (JD): Defines required technical and professional expectations.
2. RESUME: Candidate’s claimed skills, tools, and project experience.
3. TRANSCRIPT: The full interview Q&A conversation.

EVALUATION CRITERIA:

1. Relevance:
   - Did the candidate directly answer the question asked?
   - Did they avoid unnecessary vague or unrelated information?

2. Technical Accuracy:
   - Are the technical explanations correct?
   - Is the depth appropriate for the role?
   - Did they demonstrate practical understanding or only theoretical knowledge?

3. Communication:
   - Was the explanation clear, structured, and confident?
   - Did they communicate professionally?

4. Resume Consistency:
   - Do the answers align with the claims made in the resume?
   - If the candidate cannot explain their own mentioned projects clearly, reduce score significantly.

5. Strict Decision Rules (MANDATORY):
   - If the candidate does not attend the interview → recommendation MUST be "Reject".
   - If the candidate joins the interview and leaves the interview without giving greeting of themself even after agent asking for it→ recommendation MUST be "Reject".
   - If the candidate is joined and not answered frist question and get disconnected → recommendation MUST be "Reject".
   - If the candidate skips more than 2 questions → recommendation MUST be "Reject".
   - If the candidate says "I don't remember" or shows poor understanding of their own project → recommendation MUST be "Reject".
   - If the candidate avoids answering multiple technical questions → recommendation MUST be "Reject".
   - If the candidate does not answer any question properly and leaves the meeting / disconnects / refuses to answer → recommendation MUST be "Reject".
   - If technical fundamentals are completely incorrect for the role → recommendation MUST be "Reject".

6. Scoring Guidelines:
   - 9-10: Strong technical depth, confident, job-ready.
   - 7-8: Good understanding, minor gaps.
   - 5-6: Basic understanding but lacks depth.
   - 3-4: Weak technical clarity.
   - 1-2: No meaningful technical competency.
   -1-0 : if meeting joined and leaved and not answered any question and also not introducting temself even after asked must give 0 score and recommendation MUST be "Reject".

OUTPUT FORMAT:
You must return strictly VALID JSON.
Do NOT add explanations.
Do NOT add markdown.
Do NOT add extra text.
Return ONLY valid JSON.

Structure:
{{
    "candidate_name": "Extract from Resume",
    "overall_score": (Integer 1-10),
    "technical_score": (Integer 1-10),
    "communication_score": (Integer 1-10),
    "recommendation": "Strong Hire" | "Hire" | "Reject",
    "summary": "Executive summary in maximum 3 concise sentences.",
    "detailed_feedback": [
        {{
            "question": "Exact question asked",
            "candidate_answer_summary": "Brief summary of their answer",
            "score": (1-10),
            "feedback": "Precise technical evaluation explaining strengths and gaps."
        }}
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
    
