import io
import tempfile
import os
import re
import wave
import numpy as np
import speech_recognition as sr

# Load local Faster-Whisper 'small' model (Vastly superior Thai speech recognition accuracy)
whisper_model = None
try:
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    print("[STT] Local Faster-Whisper 'small' high-accuracy model loaded!")
except Exception as e:
    print(f"[STT Error] Faster-Whisper init: {e}")

class STTTranscriber:
    """High-accuracy Thai Speech-to-Text with Peak Audio Normalization & Phonetic Corrector."""

    CORRECTION_MAP = {
        r"กิติ": "ก็อดจิ",
        r"กับที่": "ก็อดจิ",
        r"ชิครับที่": "ก็อดจิ",
        r"กอดจิ": "ก็อดจิ",
        r"ก็อตจิ": "ก็อดจิ",
        r"ก๊อดจิ": "ก็อดจิ",
        r"ก็อดจี้": "ก็อดจิ",
        r"นิ่งเวอร์": "หนึ่งบวก",
        r"ก็อด": "ก็อดจิ",
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
    def _normalize_wav_audio(cls, wav_bytes: bytes) -> bytes:
        """Normalize audio peak volume to 95% maximum amplitude for maximum STT clarity."""
        try:
            with io.BytesIO(wav_bytes) as in_io:
                with wave.open(in_io, 'rb') as wf:
                    params = wf.getparams()
                    frames = wf.readframes(params.nframes)

            # Convert 16-bit PCM bytes to numpy array
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            max_val = np.max(np.abs(audio_data))
            
            if max_val > 10:
                # Target peak amplitude: 28000 (approx 85-90% of int16 max 32767)
                scale_factor = 28000.0 / max_val
                audio_data = np.clip(audio_data * scale_factor, -32767, 32767).astype(np.int16)

            out_io = io.BytesIO()
            with wave.open(out_io, 'wb') as wf:
                wf.setparams(params)
                wf.writeframes(audio_data.tobytes())
            
            return out_io.getvalue()
        except Exception as e:
            print(f"[STT Audio Normalize Warning]: {e}")
            return wav_bytes

    @classmethod
    def transcribe_audio_bytes(cls, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        # Normalize audio volume peak for ultra clarity
        normalized_bytes = cls._normalize_wav_audio(audio_bytes)

        tmp_wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(normalized_bytes)
                tmp_wav_path = tmp_file.name

            # Method 1: Google SpeechRecognition th-TH (Primary)
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(tmp_wav_path) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    audio_data = recognizer.record(source)

                text = recognizer.recognize_google(audio_data, language="th-TH")
                text = cls._correct_godji_phonetics(text)
                if text and text.strip():
                    print(f"[Google STT] Transcribed Thai Text: '{text}'")
                    return text
            except Exception as ge:
                print(f"[Google STT Fallback]: {ge}")

            # Method 2: Local Faster-Whisper 'small' Model (High Accuracy Fallback)
            if whisper_model:
                try:
                    segments, _ = whisper_model.transcribe(
                        tmp_wav_path,
                        language="th",
                        initial_prompt="ก็อดจิ Godji AI Godji สวัสดีครับ"
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
