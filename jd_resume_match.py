import google.generativeai as genai
import os
import numpy as np

genai.configure(api_key=os.getenv("gemini_api_key"))
embed_model = "models/text-embedding-004"

def get_embedding(text: str) -> list:
    """
    generate embedding for the given text
    """
    if not text or not text.strip():
        return []

    result = genai.embed_content(
        model=embed_model,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def cosin_similarity(embedding1: list, embedding2: list) -> float:
    """
    compute cosin similarity between two embedding vectors
    """
    if not embedding1 or not embedding2:
        return 0.0

    v1 = np.array(embedding1)
    v2 = np.array(embedding2)
    
    demon = np.linalg.norm(v1) * np.linalg.norm(v2)
    if demon == 0.0:
        return 0.0
    return float(np.dot(v1, v2) / demon)

def match_resume_jd(resume_json: dict, jd_json: dict) -> dict:
    """
    match resume and jd using embeddings + cosine similarity
    """
    if "error" in resume_json or "error" in jd_json:
        return {"match_score": 0.0, "match_percentage": 0.0, "status": "Error in parsing input"}
    # Handle cases where skills might be a string or a list
    resume_skills = resume_json.get('Skills', [])
    if isinstance(resume_skills, list):
        resume_skills_text = ', '.join(resume_skills)
    else:
        resume_skills_text = str(resume_skills)

    jd_skills = jd_json.get('Required skills', [])
    if isinstance(jd_skills, list):
        jd_skills_text = ', '.join(jd_skills)
    else:
        jd_skills_text = str(jd_skills)

    resume_text = f"""
    skills: {resume_skills_text}
    experience: {resume_json.get('Experience', '')}
    education: {resume_json.get('Education', '')}
    """

    jd_text = f"""
    required_skills: {jd_skills_text}
    required_experience: {jd_json.get('Required experience', '')}
    required_education: {jd_json.get('Required education', '')}
    """

    resume_embedding = get_embedding(resume_text)
    jd_embedding = get_embedding(jd_text)


    similarity_score = cosin_similarity(resume_embedding, jd_embedding)

    return {
        "match_score": round(similarity_score, 4),
        "match_percentage": round(similarity_score * 100, 2),
        "status": _match_label(similarity_score)
    }

def _match_label(score: float) -> str:
    """
    Human readable match label
    """
    if score >= 0.85:
        return "Excellent Match"
    elif score >= 0.65:
        return "Good Match"
    elif score >= 0.45:
        return "Partial Match"
    else:
        return "Low Match"
