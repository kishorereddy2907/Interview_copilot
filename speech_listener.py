import queue
import json
import time
import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

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

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")


def azure_stt_available() -> tuple[bool, str]:
    if not AZURE_SPEECH_KEY:
        return False, "AZURE_SPEECH_KEY is not set in .env"
    if not AZURE_SPEECH_REGION:
        return False, "AZURE_SPEECH_REGION is not set in .env"
    return True, ""

model = Model(VOSK_MODEL_PATH) if Model is not None else None


def stt_available() -> tuple[bool, str]:
    """Return whether live microphone STT can run in current environment."""
    vosk_available, vosk_reason = _vosk_stt_available()
    azure_available, azure_reason = azure_stt_available()

    if vosk_available:
        return True, "vosk"
    elif azure_available:
        return True, "azure"
    else:
        return False, f"Vosk STT unavailable: {vosk_reason}. Azure STT unavailable: {azure_reason}"

def _vosk_stt_available() -> tuple[bool, str]:
    if Model is None or KaldiRecognizer is None:
        return False, f"vosk import failed: {VOSK_IMPORT_ERROR}"
    if sd is None:
        return False, f"sounddevice import failed: {STT_IMPORT_ERROR}"
    return True, ""


def listen_stream(stt_service: str = "vosk", silence_timeout: float = 1.2, max_duration: float = 30.0):
    if stt_service == "azure":
        yield from _listen_stream_azure(silence_timeout=silence_timeout, max_duration=max_duration)
    else:
        yield from _listen_stream_vosk(silence_timeout=silence_timeout, max_duration=max_duration)

def _listen_stream_vosk(silence_timeout: float = 1.2, max_duration: float = 30.0):
    available, reason = _vosk_stt_available()
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

def _listen_stream_azure(silence_timeout: float = 1.2, max_duration: float = 30.0):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    done = False
    final_text = ""
    recognized_queue = queue.Queue()

    def recognized_cb(evt):
        nonlocal final_text
        if evt.result.text:
            final_text += " " + evt.result.text
            recognized_queue.put(final_text.strip())

    def recognizing_cb(evt):
        if evt.result.text:
            recognized_queue.put((final_text + " " + evt.result.text).strip())

    def stop_cb(evt):
        nonlocal done
        done = True

    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.session_started.connect(lambda evt: print("SESSION STARTED: {}".format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print("SESSION STOPPED {}".format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print("CANCELED {}".format(evt)))

    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    speech_recognizer.start_continuous_recognition()
    start_time = time.time()
    last_text_time = time.time()

    while not done:
        if time.time() - start_time > max_duration:
            break
        try:
            text = recognized_queue.get(timeout=0.1)
            yield text
            last_text_time = time.time()
        except queue.Empty:
            if time.time() - last_text_time > silence_timeout:
                break
            continue

    speech_recognizer.stop_continuous_recognition()

    if final_text.strip():
        yield final_text.strip()


def listen_once_streamed(stt_service: str = "vosk") -> str:
    last = ""
    for chunk in listen_stream(stt_service=stt_service):
        last = chunk
    return last
