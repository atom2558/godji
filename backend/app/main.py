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
                image_bytes = base64.b64decode(image_b64) if image_b64 and is_streaming_active else None
                
                chat_res = await gemini_client.chat_with_godji(user_msg, image_bytes)
                await websocket.send_json({
                    "type": "chat_reply",
                    "reply": chat_res.get("reply"),
                    "cli_command": chat_res.get("cli_command"),
                    "cli_output": chat_res.get("cli_output")
                })
            elif packet_type == "voice_chat":
                audio_b64 = packet.get("audio", "")
                mime_type = packet.get("mime_type", "audio/webm")
                image_b64 = packet.get("image", None)
                
                audio_bytes = base64.b64decode(audio_b64)
                image_bytes = base64.b64decode(image_b64) if image_b64 and is_streaming_active else None
                
                transcribed_text = await asyncio.to_thread(STTTranscriber.transcribe_audio_bytes, audio_bytes, mime_type)

                if transcribed_text and transcribed_text.strip():
                    print(f"[STT Voice Text] '{transcribed_text}'")
                    voice_res = await gemini_client.chat_with_godji(transcribed_text, image_bytes)
                    reply_msg = voice_res.get("reply")
                    cli_cmd = voice_res.get("cli_command")
                    cli_output = voice_res.get("cli_output")
                else:
                    print("[STT Voice Text] Empty or silent audio")
                    transcribed_text = None
                    reply_msg = "ไม่ได้ยินเสียงพูด หรือเสียงเบาเกินไป โปรดกดไมค์แล้วพูดใหม่อีกครั้งครับ"
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
