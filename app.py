import streamlit as st
import os
import json
import time

from resume_parser import parse_resume
from interview_engine import InterviewEngine
from speech_listener import listen_stream, stt_available

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
        "- Generate answer (streaming)"
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

stt_is_ready, stt_error = stt_available()


def render_streamed_answer(question: str):
    st.markdown("### 🧑‍💼 Interview Question")
    st.write(question)
    st.markdown("### 🤖 Suggested Answer (Streaming)")

    answer_placeholder = st.empty()
    full_answer = ""
    for chunk in engine.stream_answer(
        question,
        answer_style=answer_style,
        include_follow_up=include_follow_up,
    ):
        full_answer += chunk
        answer_placeholder.markdown(full_answer)

    if include_follow_up:
        st.markdown("### 🔮 Likely Follow-up & Prep")
        st.write(engine.suggest_follow_up(question, full_answer))


if mode == "Copilot (Live Interview)":
    st.subheader("🎧 Live Interview Copilot")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎤 Listen", disabled=not stt_is_ready):
            st.session_state.listening = True
            st.session_state.live_text = ""
            st.session_state.final_question = ""
    with col2:
        st.caption("Live transcription (auto-stops on silence)")

    if not stt_is_ready:
        st.warning(f"Live STT unavailable in this environment: {stt_error}")

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
            render_streamed_answer(interviewer_question)
            with open("sessions.json", "w", encoding="utf-8") as f:
                json.dump(engine.history, f, indent=2)
        except Exception as exc:
            st.error(f"⚠️ AI error: {exc}")

else:
    st.subheader("🧪 Interview Simulation")

    if st.button("Ask Next Question"):
        try:
            question = engine.ask_question()
            render_streamed_answer(question)
            with open("sessions.json", "w", encoding="utf-8") as f:
                json.dump(engine.history, f, indent=2)
        except Exception as exc:
            st.error(f"⚠️ AI error: {exc}")
