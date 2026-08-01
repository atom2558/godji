import io
import tempfile
import os
import speech_recognition as sr

# Load local Faster-Whisper model for 100% offline Speech-to-Text
whisper_model = None
try:
    from faster_whisper import WhisperModel
    # Load fast tiny model for fast 0.2s CPU transcription
    whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("[STT] Local Faster-Whisper model loaded successfully!")
except Exception as e:
    print(f"[STT Error] Faster-Whisper init: {e}")

class STTTranscriber:
    """Converts native WAV audio bytes to Thai text using local Faster-Whisper or SpeechRecognition."""

    @classmethod
    def transcribe_audio_bytes(cls, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        tmp_wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_wav_path = tmp_file.name

            # Method 1: Local Faster-Whisper (100% Offline, Zero ffprobe needed)
            if whisper_model:
                try:
                    segments, _ = whisper_model.transcribe(tmp_wav_path, language="th")
                    text = "".join([segment.text for segment in segments]).strip()
                    if text:
                        print(f"[Faster-Whisper STT] Transcribed Thai Text: '{text}'")
                        return text
                except Exception as we:
                    print(f"[Faster-Whisper STT Error]: {we}")

            # Method 2: Google SpeechRecognition Fallback
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_wav_path) as source:
                audio_data = recognizer.record(source)

            text = recognizer.recognize_google(audio_data, language="th-TH")
            print(f"[Google STT] Transcribed Thai Text: '{text}'")
            return text

        except sr.UnknownValueError:
            print("[STT] Speech Recognition: Silent or quiet audio")
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
