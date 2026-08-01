import io
import tempfile
import os
import speech_recognition as sr
from pydub import AudioSegment

class STTTranscriber:
    """Converts audio bytes (webm/wav) to Thai text using SpeechRecognition."""

    @classmethod
    def transcribe_audio_bytes(cls, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        if not audio_bytes:
            return ""

        tmp_wav_path = None
        try:
            audio_format = "webm"
            if "wav" in mime_type:
                audio_format = "wav"
            elif "ogg" in mime_type:
                audio_format = "ogg"

            sound = AudioSegment.from_file(io.BytesIO(audio_bytes), format=audio_format)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_wav_path = tmp_file.name

            sound.export(tmp_wav_path, format="wav")

            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_wav_path) as source:
                audio_data = recognizer.record(source)

            text = recognizer.recognize_google(audio_data, language="th-TH")
            print(f"🎙️ [STT] Transcribed Audio -> Thai Text: '{text}'")
            return text

        except sr.UnknownValueError:
            print("🎙️ [STT] Speech Recognition could not understand audio")
            return ""
        except Exception as e:
            print(f"⚠️ [STT] Error transcribing audio: {e}")
            return ""
        finally:
            if tmp_wav_path and os.path.exists(tmp_wav_path):
                try:
                    os.remove(tmp_wav_path)
                except Exception:
                    pass
