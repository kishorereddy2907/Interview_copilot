import streamlit as st
import json
import os
from resume_parser import parse_resume
from interview_engine import InterviewEngine

st.set_page_config(
    page_title="Local AI Interview Copilot",
    layout="centered"
)

st.title("🧠 Local AI Interview Copilot")
st.caption("Powered by Gemini 3 Flash Preview")

# Sidebar controls
with st.sidebar:
    st.header("Interview Settings")
    interview_type = st.selectbox(
        "Interview Type",
        ["technical", "hr"]
    )

    st.markdown("---")
    st.markdown("**Instructions**")
    st.markdown(
        "- Upload your resume\n"
        "- Click *Ask next question*\n"
        "- Review AI-generated answers\n"
    )

# Resume upload
resume_file = st.file_uploader(
    "Upload your resume (PDF or DOCX)",
    type=["pdf", "docx"]
)

if resume_file:
    # Save resume locally
    os.makedirs("resume", exist_ok=True)
    resume_path = os.path.join("resume", resume_file.name)

    with open(resume_path, "wb") as f:
        f.write(resume_file.getbuffer())

    # Parse resume
    resume_text = parse_resume(resume_path)

    # Initialize interview engine once
    if "engine" not in st.session_state:
        st.session_state.engine = InterviewEngine(
            resume_context=resume_text,
            interview_type=interview_type
        )

    st.success("Resume loaded successfully")

    # Ask next question
    if st.button("Ask next question"):
        engine = st.session_state.engine

        try:
            question = engine.ask_question()
            answer = engine.generate_answer(question)

            st.markdown("### 🧑‍💼 Interview Question")
            st.write(question)

            st.markdown("### 🤖 Suggested Answer")
            st.write(answer)

        except Exception as e:
            st.error(
                "⚠️ The AI model is temporarily busy. "
                "Please wait a few seconds and try again."
            )


else:
    st.info("Please upload a resume to begin the interview.")
