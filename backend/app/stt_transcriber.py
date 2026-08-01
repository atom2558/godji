import io
import tempfile
import os
import speech_recognition as sr
from pydub import AudioSegment

try:
    import imageio_ffmpeg
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    pass

# Try loading local Faster-Whisper model for 100% offline Speech-to-Text (ADA V2 Style)
whisper_model = None
try:
    from faster_whisper import WhisperModel
    # Load fast tiny model (int8 CPU quantised for speed)
    whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("[STT] Local Faster-Whisper model loaded successfully!")
except Exception as e:
    print(f"[STT Error] Faster-Whisper init: {e}")

class STTTranscriber:
    """Converts audio bytes (webm/wav) to Thai text using local Faster-Whisper or SpeechRecognition."""

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

            # Method 1: Local Faster-Whisper (100% Offline, ADA V2 Style)
            if whisper_model:
                try:
                    segments, _ = whisper_model.transcribe(tmp_wav_path, language="th")
                    text = "".join([segment.text for segment in segments]).strip()
                    if text:
                        print(f"[Faster-Whisper STT] Transcribed: '{text}'")
                        return text
                except Exception as we:
                    print(f"[Faster-Whisper STT Error]: {we}")

            # Method 2: Google SpeechRecognition Fallback
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_wav_path) as source:
                audio_data = recognizer.record(source)

            text = recognizer.recognize_google(audio_data, language="th-TH")
            print(f"[Google STT] Transcribed: '{text}'")
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
