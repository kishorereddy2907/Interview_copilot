from datetime import datetime
from google import genai
from dotenv import load_dotenv
import os
import time
from google.genai.errors import ServerError

# Load environment variables from .env
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Use Gemini 3 Flash Preview (fast + free-tier friendly when enabled)
MODEL_NAME = "models/gemini-3-flash-preview"


def extract_text(response) -> str:
    """
    Safely extract text from Gemini responses.
    Works across Gemini 2.x, Gemini 3 preview, and future models.
    """
    # Case 1: response.text exists and is populated
    if hasattr(response, "text") and response.text:
        return response.text.strip()

    # Case 2: Structured candidates (common in preview / agentic models)
    if hasattr(response, "candidates"):
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        return part.text.strip()

    # If we reach here, Gemini returned something unexpected
    raise ValueError("No text content found in Gemini response")
def generate_with_retry(prompt: str, max_retries: int = 3, delay: float = 1.5):
    """
    Retry Gemini calls when model is temporarily overloaded (503).
    """
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
        except ServerError as e:
            if "503" in str(e) and attempt < max_retries:
                time.sleep(delay * attempt)  # exponential backoff
            else:
                raise


class InterviewEngine:
    def __init__(self, resume_context: str, interview_type: str = "technical"):
        self.resume_context = resume_context
        self.interview_type = interview_type
        self.history = []
        self.turn = 0

    def _load_prompt(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def ask_question(self) -> str:
        prompt = self._load_prompt("prompts/interviewer.txt").format(
            interview_type=self.interview_type,
            resume_context=self.resume_context
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        question = extract_text(response)

        self.history.append({
            "turn": self.turn,
            "question": question,
            "timestamp": datetime.utcnow().isoformat()
        })

        self.turn += 1
        return question

    def generate_answer(self, question: str) -> str:
        prompt = self._load_prompt("prompts/answer_generator.txt").format(
            resume_context=self.resume_context,
            question=question
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        answer = extract_text(response)
        self.history[-1]["answer"] = answer

        return answer
