import sys
import os
from dotenv import load_dotenv
import uuid
from pymongo import MongoClient
from datetime import datetim
# Load environment variables
load_dotenv()

# Ensure local libraries are found first
lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

import streamlit as st
import json
import os
from jd_resume_match import match_resume_jd
from resume_prasing import prase_resume
from jd_prasing import jd_prase
from text_extract import extract_text
from question_gen import generate_questions

st.set_page_config(page_title="Resume JD Analyser", layout="wide")

st.title("resume jd analyser")

st.subheader("upload Resume")
resume_file = st.file_uploader("upload Resume",type=["pdf","docx","doc"])

st.subheader("upload job description")
jd_text = st.text_area("job description",
height=200,placeholder="paste job description here"
)
if st.button("Analyse"):
    if resume_file is None or not jd_text.strip():
        st.warning("please upload resume and job description")
        st.stop()
    
    temp_path = f"temp_{resume_file.name}"
    with open(temp_path, "wb") as f:
        f.write(resume_file.getbuffer())

    try:
        with st.spinner("Extracting resume text..."):
            resume_text = extract_text(temp_path)
            st.success("Resume text extracted")

        with st.spinner("Prasing resume..."):
            resume_json = prase_resume(resume_text)
            st.success("Resume parsed")

        with st.spinner("Prasing job description..."):
            jd_json = jd_prase(jd_text)
            st.success("Job description parsed")

        # with st.spinner("Matching resume and job description..."):
        #     match_result = match_resume_jd(resume_json, jd_json)
        #     st.success("Resume and job description matched")

        with st.spinner("Generating questions..."):
            questions = generate_questions(resume_json, jd_json)
            st.success("Questions generated")

        st.success("Analyse completed")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Resume")
            st.write(resume_json)

        with col2:
            st.subheader("Job description")
            st.write(jd_json)

        # st.subheader("Match Result")
        # st.write(match_result)

        st.subheader("Interview Questions")
        st.write(questions)

    except Exception as e:
        st.error(f"Error: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)