# Interview Copilot Project Architecture

This document details the current architecture of the `Interview_copilot` project and proposes enhancements based on best practices observed in other open-source AI interview assistant projects.

## Current Architecture Overview

The `Interview_copilot` project is a Python-based application leveraging Streamlit for its user interface. It integrates with Google's Gemini API for AI-driven question generation and answer suggestions, and utilizes a local Vosk model for speech-to-text (STT) capabilities. The project is structured as follows:

*   **`app.py`**: The main Streamlit application file, handling UI rendering, user input, and orchestrating calls to other modules.
*   **`interview_engine.py`**: Contains the core logic for interacting with the Gemini API, managing interview history, generating questions, streaming answers, and suggesting follow-up questions. It uses prompt templates stored in the `prompts/` directory.
*   **`speech_listener.py`**: Manages the speech-to-text functionality, likely utilizing the Vosk library and model for local audio processing.
*   **`resume_parser.py`**: Responsible for parsing resume files (PDF, DOCX) to extract relevant information for the AI engine.
*   **`prompts/`**: A directory containing text files with prompt templates used by the `interview_engine.py` for various AI tasks.
*   **`vosk_model/`**: Stores the local Vosk speech recognition model.
*   **`.env`**: Environment file for storing API keys (e.g., `GEMINI_API_KEY`).

### Data Flow

1.  **Resume Upload**: The user uploads a resume (PDF/DOCX) via the Streamlit UI.
2.  **Resume Parsing**: `resume_parser.py` extracts text from the resume.
3.  **Interview Engine Initialization**: An `InterviewEngine` instance is created with the parsed resume context and interview type.
4.  **Speech-to-Text (STT)**:
    *   In "Copilot" mode, `speech_listener.py` captures audio (from microphone) and transcribes interviewer questions in real-time using Vosk.
    *   The transcribed text is displayed in the UI and can be edited by the user.
5.  **AI Interaction (Gemini API)**:
    *   **Question Generation (Simulation Mode)**: `interview_engine.py` uses a prompt from `prompts/interviewer.txt` and the resume context to generate interview questions via the Gemini API.
    *   **Answer Generation (Copilot & Simulation Modes)**: When a question is provided, `interview_engine.py` uses a prompt from `prompts/answer_generator.txt`, resume context, and the question to stream an AI-generated answer via the Gemini API.
    *   **Follow-up Suggestion**: Optionally, `interview_engine.py` uses `prompts/followup_generator.txt` to suggest likely follow-up questions.
6.  **History Management**: Interview questions and AI-generated answers are stored in `engine.history` and saved to `sessions.json`.

## Proposed Enhancements and Future Directions

Based on the research of other interview copilot projects, the following enhancements could be considered to improve the `Interview_copilot` project:

1.  **Frontend Modernization (Optional but Recommended)**:
    *   While Streamlit provides a quick way to build interactive apps, migrating to a dedicated web framework like **Next.js with React** could offer greater flexibility, performance, and a more polished user experience, especially for features like Picture-in-Picture (PiP) mode and custom overlays.
    *   **Tailwind CSS** can be integrated for efficient and scalable styling.

2.  **Advanced Speech-to-Text (STT) Integration**:
    *   **System Audio Capture**: Implement robust system audio capture for the interviewer's voice. This is a critical feature for a true 
copilot. This might involve exploring browser extensions or platform-specific solutions for web-based applications, or more advanced audio routing for desktop applications.
    *   **Alternative STT Services**: While Vosk is good for local processing, integrating with cloud-based STT services like **Azure Cognitive Services Speech SDK** or Google Cloud Speech-to-Text could offer higher accuracy and better language support, especially for diverse accents and complex technical jargon.

3.  **Enhanced LLM Integration**:
    *   **Multi-LLM Support**: The current project uses Gemini. Expanding to include **OpenAI GPT models** (e.g., GPT-4, GPT-4o) would provide users with more choices and potentially better performance for specific tasks.
    *   **Context Management**: Improve the management of conversational context to ensure the AI provides highly relevant and coherent responses throughout the interview. This could involve more sophisticated prompt engineering or fine-tuning of LLMs.

4.  **Discreet UI/UX for Copilot Mode**:
    *   **Picture-in-Picture (PiP) Mode**: Implement a true PiP mode or an overlay that can float above other applications, allowing the user to see AI suggestions without switching windows or making it obvious they are using an assistant.
    *   **Customizable Overlays**: Allow users to customize the appearance and position of the AI suggestion overlay.

5.  **Robust Error Handling and User Feedback**:
    *   Improve error messages and provide clearer guidance to users when API keys are invalid or services are unavailable.
    *   Implement logging for debugging and performance monitoring.

6.  **Testing and Evaluation**:
    *   Develop a comprehensive testing suite for STT accuracy, LLM response quality, and overall system performance.
    *   Consider A/B testing different prompt strategies or LLM configurations.

## Implementation Roadmap (Initial Steps)

1.  **Review and Refine Existing Code**: Understand the current implementation of `speech_listener.py` and `interview_engine.py` thoroughly.
2.  **Integrate Azure Speech SDK**: Begin by replacing or augmenting the Vosk STT with Azure Cognitive Services Speech SDK for improved accuracy. This will involve obtaining Azure API keys and integrating the SDK into `speech_listener.py`.
3.  **Add OpenAI API Support**: Modify `interview_engine.py` to allow switching between Gemini and OpenAI models, requiring the setup of OpenAI API keys and corresponding API calls.
4.  **Develop a Basic Overlay/PiP Concept**: For the Streamlit application, explore options for creating a discreet overlay or a separate window that can display AI suggestions without interfering with the main interview window. This might involve using Streamlit components or external libraries.

This architectural document will serve as a guide for the development of the enhanced AI Interview Copilot, ensuring a structured approach to building a robust and feature-rich application.
