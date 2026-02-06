from datetime import datetime
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError

# -------------------------------------------------
# Environment & Client
# -------------------------------------------------
load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Primary = fast preview (may overload)
FALLBACK_MODEL = "models/gemini-3-flash-preview"

# Fallback = stable free-tier model
PRIMARY_MODEL = "models/gemini-flash-latest"


# -------------------------------------------------
# Response text extraction (preview-safe)
# -------------------------------------------------
def extract_text(response) -> str:
    """
    Safely extract text from Gemini responses across
    preview and stable models.
    """
    # Case 1: Convenience field
    if hasattr(response, "text") and response.text:
        return response.text.strip()

    # Case 2: Structured response (preview models)
    if hasattr(response, "candidates"):
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        return part.text.strip()

    raise ValueError("No text content found in Gemini response")


# -------------------------------------------------
# Gemini call with retry + fallback
# -------------------------------------------------
def generate_with_fallback(prompt: str, max_retries: int = 2):
    """
    1. Try preview model with retries
    2. On overload / rate limit → fallback to stable model
    """
    # ---- Try primary (preview) model ----
    for attempt in range(1, max_retries + 1):
        try:
            # return client.models.generate_content(
            #     model=PRIMARY_MODEL,
            #     contents=prompt
            # )
            return client.models.generate_content_stream(
                model=PRIMARY_MODEL,
                contents=prompt
            )
            for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
        except (ServerError, ClientError):
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
            else:
                break

    # ---- Fallback to stable model ----
    return client.models.generate_content(
        model=FALLBACK_MODEL,
        contents=prompt
    )


# -------------------------------------------------
# Interview Engine
# -------------------------------------------------
class InterviewEngine:
    def __init__(self, resume_context: str, interview_type: str = "technical"):
        self.resume_context = resume_context
        self.interview_type = interview_type
        self.history = []
        self.turn = 0

    def _load_prompt(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # -------------------------------------------------
    # Simulation mode: AI asks question
    # -------------------------------------------------
    def ask_question(self) -> str:
        prompt = self._load_prompt("prompts/interviewer.txt").format(
            interview_type=self.interview_type,
            resume_context=self.resume_context
        )

        response = generate_with_fallback(prompt)
        question = extract_text(response)

        self.history.append({
            "turn": self.turn,
            "question": question,
            "timestamp": datetime.utcnow().isoformat()
        })

        self.turn += 1
        return question

    # -------------------------------------------------
    # Copilot mode: AI answers interviewer question
    # -------------------------------------------------
    def generate_answer(self, question: str) -> str:
        prompt = self._load_prompt("prompts/answer_generator.txt").format(
            resume_context=self.resume_context,
            question=question
        )

        response = generate_with_fallback(prompt)
        answer = extract_text(response)

        # Attach answer to last turn if exists
        if self.history:
            self.history[-1]["answer"] = answer

        return answer
