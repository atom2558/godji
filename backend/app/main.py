import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.gemini_client import GeminiAssistantClient
from app.vision_parser import VisionParser
from app.cli_tools import CLISystemAgent
from app.ollama_gatekeeper import OllamaGatekeeper
from app.stt_transcriber import STTTranscriber

app = FastAPI(
    title="AI Godji Backend API",
    description="Multimodal Desktop Assistant with Computer Vision and CLI Execution Capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_client = GeminiAssistantClient(api_key=GEMINI_API_KEY)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

prev_frame_bytes = None
is_streaming_active = False

STRICT_WAKE_WORDS = ["ก็อดจิ", "กอดจิ", "ก็อตจิ", "ก๊อดจิ", "godji", "ก็อด"]
VISION_NEED_KEYWORDS = [
    "หน้าจอ", "บทความ", "ภาพ", "ตรงนี้", "ช่วยดู", "มองดู", "ดูให้", 
    "อ่านให้", "หน้าจอนี้", "รูปนี้", "ปุ่ม", "แอป", "screen", "look", "บทความนี้"
]

def check_wake_word(text: str):
    if not text or not text.strip():
        return False
    lower = text.lower()
    return any(w in lower for w in STRICT_WAKE_WORDS)

def needs_screen_vision(text: str):
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in VISION_NEED_KEYWORDS)

@app.get("/")
def read_root():
    return {
        "app": "AI Godji Backend Server",
        "status": "Online",
        "gemini_api_key_configured": bool(GEMINI_API_KEY)
    }

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    global prev_frame_bytes, is_streaming_active
    await websocket.accept()
    print("[WebSocket] Client connected to /ws/live endpoint")

    try:
        while True:
            data_text = await websocket.receive_text()
            packet = json.loads(data_text)
            packet_type = packet.get("type")

            if packet_type == "frame":
                is_streaming_active = True
                image_b64 = packet.get("image", "")
                if not image_b64:
                    continue

                curr_frame_bytes = base64.b64decode(image_b64)
                has_changed = VisionParser.detect_motion_or_changes(prev_frame_bytes, curr_frame_bytes)

                if has_changed:
                    prev_frame_bytes = curr_frame_bytes
                    hud_data = await gemini_client.analyze_screen_frame(curr_frame_bytes)
                    await websocket.send_json({
                        "type": "hud_update",
                        "data": hud_data
                    })
                    
            elif packet_type == "cli":
                tool_name = packet.get("tool_name")
                tool_args = packet.get("tool_args", {})
                
                result = await gemini_client.process_cli_command(tool_name, tool_args)
                await websocket.send_json({
                    "type": "cli_result",
                    "tool_name": tool_name,
                    "result": result
                })
            elif packet_type == "chat":
                user_msg = packet.get("message", "")
                image_b64 = packet.get("image", None)
                image_bytes = base64.b64decode(image_b64) if image_b64 else None
                
                chat_res = await gemini_client.chat_with_godji(user_msg, image_bytes)
                await websocket.send_json({
                    "type": "chat_reply",
                    "reply": chat_res.get("reply"),
                    "cli_command": chat_res.get("cli_command"),
                    "cli_output": chat_res.get("cli_output")
                })
            elif packet_type == "voice_chat":
                audio_b64 = packet.get("audio", "")
                mime_type = packet.get("mime_type", "audio/wav")
                image_b64 = packet.get("image", None)
                
                audio_bytes = base64.b64decode(audio_b64)
                image_bytes = base64.b64decode(image_b64) if image_b64 else None
                
                transcribed_text = await asyncio.to_thread(STTTranscriber.transcribe_audio_bytes, audio_bytes, mime_type)

                if transcribed_text and transcribed_text.strip():
                    has_wake_word = check_wake_word(transcribed_text)
                    
                    if has_wake_word:
                        print(f"🐉 [WAKE WORD DETECTED] Prompt: '{transcribed_text}'")
                        
                        # Send immediate feedback to UI so user knows Godji heard them
                        await websocket.send_json({
                            "type": "chat_stt_result",
                            "transcribed_text": transcribed_text
                        })
                        
                        cleaned_prompt = transcribed_text
                        for w in STRICT_WAKE_WORDS:
                            cleaned_prompt = cleaned_prompt.replace(w, "").strip()

                        # If user ONLY said "ก็อดจิ" without extra prompt
                        if not cleaned_prompt or len(cleaned_prompt) < 2:
                            reply_msg = "ครับผม! มีอะไรให้ก็อดจิช่วยดูแลบอกได้เลยครับ"
                            cli_cmd = None
                            cli_output = None
                        elif needs_screen_vision(transcribed_text) and not image_bytes:
                            # AI detects that screen context is required but no image was attached: Request screenshot from client!
                            print(f"📸 [Vision Request] Prompt requires screen context: '{transcribed_text}' -> Requesting screenshot from client")
                            await websocket.send_json({
                                "type": "request_screen_snapshot",
                                "prompt": transcribed_text
                            })
                            continue
                        else:
                            voice_res = await gemini_client.chat_with_godji(transcribed_text, image_bytes)
                            reply_msg = voice_res.get("reply")
                            cli_cmd = voice_res.get("cli_command")
                            cli_output = voice_res.get("cli_output")
                    else:
                        print(f"[STT Silent Filter] Ignored audio without wake word 'ก็อดจิ': '{transcribed_text}'")
                        reply_msg = None
                        cli_cmd = None
                        cli_output = None
                else:
                    transcribed_text = None
                    reply_msg = None
                    cli_cmd = None
                    cli_output = None

                await websocket.send_json({
                    "type": "chat_reply",
                    "reply": reply_msg,
                    "cli_command": cli_cmd,
                    "cli_output": cli_output,
                    "transcribed_text": transcribed_text
                })

    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket Error] {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
