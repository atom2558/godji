import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import HOST, PORT, ALLOWED_ORIGINS
from app.gemini_client import GeminiAssistantClient
from app.vision_parser import VisionParser
from app.cli_tools import CLISystemAgent

app = FastAPI(
    title="AI Godji Backend API",
    description="Multimodal Real-time AI Desktop Assistant Backend for Render & Electron",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_client = GeminiAssistantClient()

@app.get("/")
@app.get("/health")
async def health_check():
    """Health check endpoint for Render.com deployment monitoring."""
    return {
        "status": "online",
        "service": "AI Godji Backend",
        "gemini_api_configured": bool(gemini_client.client)
    }

@app.websocket("/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    """WebSocket endpoint for receiving desktop screen frames and returning real-time Overlay HUD drawing coordinates & subtitles."""
    await websocket.accept()
    print("🔌 Client connected to /ws/live endpoint")
    prev_frame_bytes = None

    try:
        while True:
            # Receive data packet from Electron client
            data = await websocket.receive_text()
            packet = json.loads(data)

            packet_type = packet.get("type", "frame")
            
            if packet_type == "frame":
                # Base64 encoded JPEG screen capture frame
                image_b64 = packet.get("image", "")
                user_prompt = packet.get("prompt", None)
                
                if image_b64:
                    image_bytes = base64.b64decode(image_b64)
                    
                    # Local OpenCV Motion Filter: Skip frame if screen hasn't changed & no explicit user prompt
                    if not user_prompt and prev_frame_bytes:
                        has_motion = VisionParser.detect_motion_or_changes(prev_frame_bytes, image_bytes, threshold=3.0)
                        if not has_motion:
                            # Send heartbeat to keep connection alive without wasting API tokens
                            await websocket.send_json({"type": "skip", "message": "Frame unchanged"})
                            continue

                    prev_frame_bytes = image_bytes

                    # Process frame via Gemini API
                    hud_data = await gemini_client.analyze_screen_frame(image_bytes, user_prompt)
                    
                    # Return HUD canvas overlay coordinates to Electron frontend
                    await websocket.send_json({
                        "type": "hud_update",
                        "data": hud_data
                    })
                    
            elif packet_type == "cli":
                # CLI command requested by client
                tool_name = packet.get("tool_name")
                tool_args = packet.get("tool_args", {})
                
                result = await gemini_client.process_cli_command(tool_name, tool_args)
                await websocket.send_json({
                    "type": "cli_result",
                    "tool_name": tool_name,
                    "result": result
                })

    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/live endpoint")
    except Exception as e:
        print(f"⚠️ Error in /ws/live websocket stream: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
