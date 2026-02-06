import queue
import json
import time
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Path to Vosk model
VOSK_MODEL_PATH = "vosk_model"

# Audio config
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

# Load model once
model = Model(VOSK_MODEL_PATH)


def listen_stream(silence_timeout: float = 1.2, max_duration: float = 30.0):
    """
    Generator that yields partial transcription text while listening.
    Stops when silence is detected or max_duration is reached.
    """
    q = queue.Queue()
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.SetWords(False)

    last_text_time = time.time()
    start_time = time.time()
    final_text = ""

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        q.put(bytes(indata))

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        print("🎤 Listening (streaming)...")

        while True:
            # Stop if max duration exceeded
            if time.time() - start_time > max_duration:
                break

            try:
                data = q.get(timeout=0.1)
            except queue.Empty:
                # Silence detection
                if time.time() - last_text_time > silence_timeout:
                    break
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    final_text += " " + text
                    last_text_time = time.time()
                    yield final_text.strip()
            else:
                partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                if partial:
                    last_text_time = time.time()
                    yield (final_text + " " + partial).strip()

    # Emit final result once more (if any)
    if final_text.strip():
        yield final_text.strip()


def listen_once_streamed() -> str:
    """
    Convenience wrapper: consumes the stream and returns final text.
    """
    last = ""
    for chunk in listen_stream():
        last = chunk
    return last
