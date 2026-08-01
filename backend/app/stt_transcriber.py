import io
import tempfile
import os
import re
import speech_recognition as sr

# Load local Faster-Whisper model as secondary fallback
whisper_model = None
try:
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("[STT] Local Faster-Whisper base model loaded!")
except Exception as e:
    print(f"[STT Error] Faster-Whisper init: {e}")

class STTTranscriber:
    """Converts native WAV audio bytes to Thai text using Google SpeechRecognition (Primary) with Faster-Whisper fallback."""

    CORRECTION_MAP = {
        r"กิติ": "ก็อดจิ",
        r"กับที่": "ก็อดจิ",
        r"ชิครับที่": "ก็อดจิ",
        r"กอดจิ": "ก็อดจิ",
        r"ก็อตจิ": "ก็อดจิ",
        r"ก๊อดจิ": "ก็อดจิ",
        r"ก็อดจี้": "ก็อดจิ",
        r"นิ่งเวอร์": "หนึ่งบวก",
    }

    @classmethod
    def _correct_godji_phonetics(cls, text: str) -> str:
        if not text:
            return ""
        cleaned = text
        for pattern, replacement in cls.CORRECTION_MAP.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        return cleaned

    @classmethod
    def transcribe_audio_bytes(cls, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        tmp_wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_wav_path = tmp_file.name

            # Method 1: Google SpeechRecognition th-TH (Primary - World Class for Thai Numbers & Speech)
            try:
                recognizer = sr.Recognizer()
                recognizer.energy_threshold = 300
                with sr.AudioFile(tmp_wav_path) as source:
                    audio_data = recognizer.record(source)

                text = recognizer.recognize_google(audio_data, language="th-TH")
                text = cls._correct_godji_phonetics(text)
                if text and text.strip():
                    print(f"[Google STT] Transcribed Thai Text: '{text}'")
                    return text
            except Exception as ge:
                print(f"[Google STT Fallback]: {ge}")

            # Method 2: Local Faster-Whisper Fallback
            if whisper_model:
                try:
                    segments, _ = whisper_model.transcribe(
                        tmp_wav_path,
                        language="th",
                        initial_prompt="หนึ่ง บวก หนึ่ง บวก สอง เท่ากับ เท่าไหร่ ก็อดจิ Godji"
                    )
                    text = "".join([segment.text for segment in segments]).strip()
                    text = cls._correct_godji_phonetics(text)
                    if text:
                        print(f"[Faster-Whisper STT] Transcribed: '{text}'")
                        return text
                except Exception as we:
                    print(f"[Faster-Whisper STT Error]: {we}")

            return ""

        except Exception as e:
            print(f"[STT Error] Error transcribing audio: {e}")
            return ""
        finally:
            if tmp_wav_path and os.path.exists(tmp_wav_path):
                try:
                    os.remove(tmp_wav_path)
                except Exception:
                    pass
