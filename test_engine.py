from interview_engine import InterviewEngine

resume_text = "Data Engineer with AWS, Glue, Redshift, Airflow experience."
engine = InterviewEngine(resume_text, "technical")

q = engine.ask_question()
print("Q:", q)

a = engine.generate_answer(q)
print("A:", a)
