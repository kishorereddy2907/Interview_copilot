from datetime import datetime
import os
import time
from typing import Generator

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError
from openai import OpenAI, APIConnectionError, APIStatusError

load_dotenv()

_gemini_client = None
_gemini_api_key = None
_openai_client = None
_openai_api_key = None


class AIServiceError(RuntimeError):
    """Raised for user-actionable Gemini API issues."""


def get_gemini_client():
    """Reuse a live Gemini client so streaming requests are not tied to temporary objects."""
    global _gemini_client, _gemini_api_key

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIServiceError("GEMINI_API_KEY is missing. Add a valid API key in your .env file.")

    if _gemini_client is None or _gemini_api_key != api_key:
        _gemini_client = genai.Client(api_key=api_key)
        _gemini_api_key = api_key

    return _gemini_client

def get_openai_client():
    """Reuse a live OpenAI client."""
    global _openai_client, _openai_api_key

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is missing. Add a valid API key in your .env file.")

    if _openai_client is None or _openai_api_key != api_key:
        _openai_client = OpenAI(api_key=api_key)
        _openai_api_key = api_key

    return _openai_client

FALLBACK_MODEL = "models/gemini-flash-latest"
PRIMARY_MODEL = "models/gemini-3-flash-preview"


def _format_gemini_client_error(exc: Exception) -> AIServiceError:
    message = str(exc)
    lowered = message.lower()
    if "reported as leaked" in lowered:
        return AIServiceError(
            "Gemini API key is blocked (reported as leaked). Generate a new API key and update GEMINI_API_KEY in .env."
        )
    if "permission_denied" in lowered or "403" in lowered:
        return AIServiceError("Gemini API permission denied. Verify API key validity and project billing/access.")
    if "invalid" in lowered and "api" in lowered and "key" in lowered:
        return AIServiceError("Gemini API key is invalid. Replace GEMINI_API_KEY in .env.")
    return AIServiceError(message)

def _format_openai_client_error(exc: Exception) -> AIServiceError:
    message = str(exc)
    lowered = message.lower()
    if "incorrect api key" in lowered:
        return AIServiceError("OpenAI API key is incorrect. Replace OPENAI_API_KEY in .env.")
    if "exceeded your current quota" in lowered:
        return AIServiceError("OpenAI API quota exceeded. Check your plan and billing details.")
    return AIServiceError(message)


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


def generate_with_fallback(prompt: str, ai_service: str, max_retries: int = 2):
    """Try primary model with retries then fallback."""
    if ai_service == "gemini":
        for attempt in range(1, max_retries + 1):
            try:
                return get_gemini_client().models.generate_content(
                    model=PRIMARY_MODEL,
                    contents=prompt,
                )
            except ServerError:
                if attempt < max_retries:
                    time.sleep(0.6 * attempt)
                else:
                    break
            except ClientError as exc:
                raise _format_gemini_client_error(exc) from exc

        try:
            return get_gemini_client().models.generate_content(
                model=FALLBACK_MODEL,
                contents=prompt,
            )
        except ClientError as exc:
            raise _format_gemini_client_error(exc) from exc
    elif ai_service == "openai":
        try:
            return get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
        except APIConnectionError as exc:
            raise AIServiceError(f"OpenAI API connection error: {exc}") from exc
        except APIStatusError as exc:
            raise _format_openai_client_error(exc) from exc
    else:
        raise ValueError(f"Unknown AI service: {ai_service}")


def stream_with_fallback(prompt: str, ai_service: str) -> Generator[str, None, None]:
    """Stream partial text for faster perceived response."""
    if ai_service == "gemini":
        try:
            stream = get_gemini_client().models.generate_content_stream(
                model=PRIMARY_MODEL,
                contents=prompt,
            )
        except ServerError:
            stream = get_gemini_client().models.generate_content_stream(
                model=FALLBACK_MODEL,
                contents=prompt,
            )
        except ClientError as exc:
            raise _format_gemini_client_error(exc) from exc

        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text
    elif ai_service == "openai":
        try:
            stream = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
        except APIConnectionError as exc:
            raise AIServiceError(f"OpenAI API connection error: {exc}") from exc
        except APIStatusError as exc:
            raise _format_openai_client_error(exc) from exc

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    else:
        raise ValueError(f"Unknown AI service: {ai_service}")


class InterviewEngine:
    def __init__(self, resume_context: str, interview_type: str = "technical", ai_service: str = "gemini"):
        self.resume_context = resume_context
        self.interview_type = interview_type
        self.ai_service = ai_service
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

        response = generate_with_fallback(prompt, self.ai_service)
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

    def stream_answer(
        self,
        question: str,
        answer_style: str = "concise",
        include_follow_up: bool = True,
    ) -> Generator[str, None, None]:
        prompt = self._load_prompt("prompts/answer_generator.txt").format(
            resume_context=self.resume_context,
            question=question,
            answer_style=answer_style,
            include_follow_up="yes" if include_follow_up else "no",
        )

        full_answer = ""
        for chunk in stream_with_fallback(prompt, self.ai_service):
            full_answer += chunk
            yield chunk

        answer = full_answer.strip()
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

    def suggest_follow_up(self, question: str, answer: str) -> str:
        prompt = self._load_prompt("prompts/followup_generator.txt").format(
            interview_type=self.interview_type,
            resume_context=self.resume_context,
            question=question,
            answer=answer,
        )
        response = generate_with_fallback(prompt, self.ai_service, max_retries=1)
        return extract_text(response)
