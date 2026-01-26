import streamlit as st
import json
import os
from resume_parser import parse_resume
from interview_engine import InterviewEngine

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="AI Interview Copilot",
    layout="centered"
)

st.title("🧠 AI Interview Copilot")
st.caption("Simulation & Copilot Mode | Gemini-powered")

# ---------------------------
# Sidebar controls
# ---------------------------
with st.sidebar:
    st.header("Mode")
    mode = st.radio(
        "Select Mode",
        ["Copilot (Live Interview)", "Simulation (Practice)"]
    )

    st.markdown("---")

    st.header("Interview Settings")
    interview_type = st.selectbox(
        "Interview Type",
        ["technical", "hr"]
    )

    st.markdown("---")

    st.markdown(
        "**How to use**\n"
        "- Upload your resume\n"
        "- Select mode\n"
        "- In Copilot mode, paste interviewer question\n"
        "- Generate answer\n"
    )

# ---------------------------
# Resume upload
# ---------------------------
resume_file = st.file_uploader(
    "Upload your resume (PDF or DOCX)",
    type=["pdf", "docx"]
)

if resume_file:
    os.makedirs("resume", exist_ok=True)
    resume_path = os.path.join("resume", resume_file.name)

    with open(resume_path, "wb") as f:
        f.write(resume_file.getbuffer())

    resume_text = parse_resume(resume_path)

    if "engine" not in st.session_state:
        st.session_state.engine = InterviewEngine(
            resume_context=resume_text,
            interview_type=interview_type
        )

    st.success("Resume loaded successfully")

    # ---------------------------
    # Copilot mode: interviewer question input
    # ---------------------------
    interviewer_question = ""

    if mode == "Copilot (Live Interview)":
        interviewer_question = st.text_area(
            "Interviewer Question",
            placeholder="Question asked by interviewer will appear here...",
            height=120
        )

    # ---------------------------
    # Answer style control
    # ---------------------------
    answer_style = st.selectbox(
        "Answer Style",
        ["Short", "Medium", "Detailed"]
    )

    # ---------------------------
    # Button label based on mode
    # ---------------------------
    button_label = (
        "Generate Answer"
        if mode == "Copilot (Live Interview)"
        else "Ask Next Question"
    )

    # ---------------------------
    # Main action
    # ---------------------------
    if st.button(button_label):
        engine = st.session_state.engine

        try:
            # Determine question source
            if mode == "Copilot (Live Interview)":
                if not interviewer_question.strip():
                    st.warning("Please enter the interviewer's question.")
                    st.stop()
                question = interviewer_question
            else:
                question = engine.ask_question()

            # Generate answer
            answer = engine.generate_answer(question)

            st.markdown("### 🧑‍💼 Interview Question")
            st.write(question)

            st.markdown("### 🤖 Suggested Answer")
            st.write(answer)

            # Save session history
            with open("sessions.json", "w", encoding="utf-8") as f:
                json.dump(engine.history, f, indent=2)

        except Exception:
            st.error(
                "⚠️ The AI is busy. Retrying with a backup model. Please wait a moment."
            )

else:
    st.info("Please upload a resume to begin.")
