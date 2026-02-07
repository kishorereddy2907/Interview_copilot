import queue
import json
import time

try:
    from vosk import Model, KaldiRecognizer
    VOSK_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependent
    Model = None
    KaldiRecognizer = None
    VOSK_IMPORT_ERROR = str(exc)

try:
    import sounddevice as sd
    STT_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependent
    sd = None
    STT_IMPORT_ERROR = str(exc)

VOSK_MODEL_PATH = "vosk_model"
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

model = Model(VOSK_MODEL_PATH) if Model is not None else None


def stt_available() -> tuple[bool, str]:
    """Return whether live microphone STT can run in current environment."""
    if Model is None or KaldiRecognizer is None:
        return False, f"vosk import failed: {VOSK_IMPORT_ERROR}"
    if sd is None:
        return False, f"sounddevice import failed: {STT_IMPORT_ERROR}"
    return True, ""


def listen_stream(silence_timeout: float = 1.2, max_duration: float = 30.0):
    available, reason = stt_available()
    if not available:
        raise RuntimeError(f"Live STT unavailable: {reason}")

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
        while True:
            if time.time() - start_time > max_duration:
                break

            try:
                data = q.get(timeout=0.1)
            except queue.Empty:
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

    if final_text.strip():
        yield final_text.strip()


def listen_once_streamed() -> str:
    last = ""
    for chunk in listen_stream():
        last = chunk
    return last
