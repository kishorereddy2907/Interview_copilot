from datetime import datetime
import os
import time
from typing import Generator
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PRIMARY_MODEL = "models/gemini-flash-latest"
FALLBACK_MODEL = "models/gemini-3-flash-preview"


# -------------------------------------------------
# Response text extraction
# -------------------------------------------------
def extract_text(response) -> str:
    """Safely extract text from Gemini responses."""
    if hasattr(response, "text") and response.text:
        return response.text.strip()

    if hasattr(response, "candidates"):
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        return part.text.strip()

    raise ValueError("No text content found in Gemini response")


def generate_with_fallback(prompt: str, max_retries: int = 2):
    """Try primary model with retries then fallback."""
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=prompt,
            )
        except (ServerError, ClientError):
            if attempt < max_retries:
                time.sleep(0.6 * attempt)
            else:
                break

    return client.models.generate_content(
        model=FALLBACK_MODEL,
        contents=prompt,
    )


def stream_with_fallback(prompt: str) -> Generator[str, None, None]:
    """Stream partial text for faster perceived response."""
    stream = None
    try:
        stream = client.models.generate_content_stream(
            model=PRIMARY_MODEL,
            contents=prompt,
        )
    except (ServerError, ClientError):
        stream = client.models.generate_content_stream(
            model=FALLBACK_MODEL,
            contents=prompt,
        )

    for chunk in stream:
        if hasattr(chunk, "text") and chunk.text:
            yield chunk.text


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
            resume_context=self.resume_context,
        )

        response = generate_with_fallback(prompt)
        question = extract_text(response)

        self.history.append(
            {
                "turn": self.turn,
                "question": question,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        self.turn += 1
        return question

    def generate_answer(
        self,
        question: str,
        answer_style: str = "concise",
        include_follow_up: bool = True,
    ) -> str:
        prompt = self._load_prompt("prompts/answer_generator.txt").format(
            resume_context=self.resume_context,
            question=question,
            answer_style=answer_style,
            include_follow_up="yes" if include_follow_up else "no",
        )

        response = generate_with_fallback(prompt)
        answer = extract_text(response)

        if self.history:
            self.history[-1]["answer"] = answer
        else:
            self.history.append(
                {
                    "turn": self.turn,
                    "question": question,
                    "answer": answer,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            self.turn += 1

        return answer

    def suggest_follow_up(self, question: str, answer: str) -> str:
        prompt = self._load_prompt("prompts/followup_generator.txt").format(
            interview_type=self.interview_type,
            resume_context=self.resume_context,
            question=question,
            answer=answer,
        )
        response = generate_with_fallback(prompt)
        return extract_text(response)
