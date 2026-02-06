import streamlit as st
import os
import json
import time

from resume_parser import parse_resume
from interview_engine import InterviewEngine
from speech_listener import listen_stream

st.set_page_config(page_title="AI Interview Copilot", layout="centered")

st.title("🧠 AI Interview Copilot")
st.caption("Copilot & Simulation Mode | Live Speech-to-Text | Parakeet-style prep")

if "engine" not in st.session_state:
    st.session_state.engine = None
if "listening" not in st.session_state:
    st.session_state.listening = False
if "live_text" not in st.session_state:
    st.session_state.live_text = ""
if "final_question" not in st.session_state:
    st.session_state.final_question = ""

with st.sidebar:
    st.header("Mode")
    mode = st.radio("Select Mode", ["Copilot (Live Interview)", "Simulation (Practice)"])

    st.markdown("---")
    interview_type = st.selectbox("Interview Type", ["technical", "hr"])

    st.markdown("---")
    answer_style = st.selectbox(
        "Answer style",
        ["concise", "detailed", "executive", "storytelling (STAR)"],
        help="Tune the answer to match the pace and tone of your interview.",
    )
    include_follow_up = st.toggle("Include likely follow-up", value=True)

    st.markdown("---")
    st.markdown(
        "**Usage**\n"
        "- Upload resume\n"
        "- In Copilot mode, click 🎤 Listen\n"
        "- Speak interviewer question\n"
        "- Edit if needed\n"
        "- Generate answer + follow-up prep"
    )

resume_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])

if not resume_file:
    st.info("Please upload a resume to begin.")
    st.stop()

os.makedirs("resume", exist_ok=True)
resume_path = os.path.join("resume", resume_file.name)

with open(resume_path, "wb") as f:
    f.write(resume_file.getbuffer())

resume_text = parse_resume(resume_path)

if st.session_state.engine is None or st.session_state.engine.interview_type != interview_type:
    st.session_state.engine = InterviewEngine(resume_context=resume_text, interview_type=interview_type)

st.success("Resume loaded")
engine = st.session_state.engine

if mode == "Copilot (Live Interview)":
    st.subheader("🎧 Live Interview Copilot")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎤 Listen"):
            st.session_state.listening = True
            st.session_state.live_text = ""
            st.session_state.final_question = ""
    with col2:
        st.caption("Live transcription (auto-stops on silence)")

    live_box = st.empty()

    if st.session_state.listening:
        for text in listen_stream():
            st.session_state.live_text = text
            live_box.text_area("Listening…", value=st.session_state.live_text, height=120)
            time.sleep(0.05)

        st.session_state.final_question = st.session_state.live_text
        st.session_state.listening = False

    interviewer_question = st.text_area(
        "Interviewer Question (editable)", value=st.session_state.final_question, height=120
    )

    if st.button("Generate Answer"):
        if not interviewer_question.strip():
            st.warning("Please provide an interview question.")
            st.stop()

        try:
            answer = engine.generate_answer(
                interviewer_question,
                answer_style=answer_style,
                include_follow_up=include_follow_up,
            )
            followup_pack = engine.suggest_follow_up(interviewer_question, answer)

            tab1, tab2 = st.tabs(["Suggested Answer", "Follow-up Prep"])
            with tab1:
                st.markdown("### 🧑‍💼 Interview Question")
                st.write(interviewer_question)
                st.markdown("### 🤖 Suggested Answer")
                st.write(answer)
            with tab2:
                st.markdown("### 🔮 Next Question Prep")
                st.write(followup_pack)

            with open("sessions.json", "w", encoding="utf-8") as f:
                json.dump(engine.history, f, indent=2)

        except Exception:
            st.error("⚠️ The AI is temporarily busy. Please wait a moment and try again.")

else:
    st.subheader("🧪 Interview Simulation")

    if st.button("Ask Next Question"):
        try:
            question = engine.ask_question()
            answer = engine.generate_answer(
                question,
                answer_style=answer_style,
                include_follow_up=include_follow_up,
            )
            followup_pack = engine.suggest_follow_up(question, answer)

            st.markdown("### 🧑‍💼 Interview Question")
            st.write(question)

            st.markdown("### 🤖 Suggested Answer")
            st.write(answer)

            st.markdown("### 🔮 Likely Follow-up & Prep")
            st.write(followup_pack)

            with open("sessions.json", "w", encoding="utf-8") as f:
                json.dump(engine.history, f, indent=2)

        except Exception:
            st.error("⚠️ The AI is temporarily busy. Please wait a moment and try again.")
