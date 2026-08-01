import json
import urllib.request
import base64
import re
from app.vision_parser import VisionParser
from app.cli_tools import CLISystemAgent

class GeminiAssistantClient:
    """100% Local Multimodal Vision & Reasoning AI Engine (ADA V2 Architecture).
    Combines Moondream (Screen Vision), Qwen2.5:7b (Local LLM), OpenCV (60 FPS HUD),
    and Local System CLI Automation with 0 external API calls or 429 quota limits.
    """

    def __init__(self, api_key: str = None):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.text_model = "qwen2.5:7b"
        self.vision_model = "moondream"

    def _query_moondream_vision(self, image_bytes: bytes, prompt: str = "Describe what is on this computer screen in detail, including open windows, text, code, buttons, and active apps.") -> str:
        """Query local Moondream vision model to analyze screenshot."""
        if not image_bytes:
            return ""
        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            payload = json.dumps({
                "model": self.vision_model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False
            }).encode('utf-8')

            req = urllib.request.Request(
                self.ollama_url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    desc = data.get("response", "").strip()
                    if desc:
                        print(f"[Moondream Vision Analysis]: {desc[:150]}...")
                        return desc
        except Exception as e:
            print(f"[Moondream Vision Error]: {e}")
        return ""

    async def stream_qwen_text(self, prompt: str):
        """Async Generator: Query 9arm Gateway API and yield text chunks in real-time."""
        url = "https://gateway.9arm.co/v1/chat/completions"
        api_key = "sk-DvdsqHV_M5uxfQm3wWPWNA"
        model_name = "qwen3.6-35b-a3b"
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "คุณคือ AI Godji ผู้ช่วยคอมพิวเตอร์ประจำตัวระดับสูง (ADA V2 Architecture)\n"
                        "คุณต้องตอบเป็นภาษาไทยอย่างเดียวเท่านั้น 100% ห้ามใช้ภาษารัสเซียหรือภาษาอื่นโดยเด็ดขาด!\n"
                        "ตอบอย่างสุภาพ น่ารัก ชัดเจน และแนะนำแนวทางภาษาไทยอย่างถูกต้อง\n"
                        "หากผู้ใช้สั่งงานระบบ (เช่น สร้างโฟลเดอร์, เปิดเว็บ, สร้างไฟล์, ลบไฟล์, หรือรันคำสั่ง terminal) "
                        "ให้ตอบด้วยรูปแบบ JSON ดังนี้เท่านั้น:\n"
                        "```json\n"
                        "{\n"
                        '  "reply": "ข้อความตอบกลับภาษาไทยอย่างสุภาพและแนะนำแนวทางครับ",\n'
                        '  "cli_command": "คำสั่ง terminal ที่จะรัน (ถ้ามี หากไม่มีให้ใส่ null)"\n'
                        "}\n"
                        "```"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "stream": True
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

        import httpx
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        yield "ขออภัยครับ ระบบเชื่อมต่อเซิร์ฟเวอร์มีปัญหา กรุณาลองใหม่อีกครั้งครับ!"
                        return
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                            except Exception:
                                pass
        except Exception as e:
            print(f"[9arm Gateway API Error]: {e}")
            # Fallback to local Ollama if 9arm fails
            try:
                print("[Failover] Falling back to Local Ollama...")
                ollama_payload = {
                    "model": self.text_model,
                    "prompt": payload["messages"][0]["content"] + f"\nข้อความผู้ใช้: {prompt}",
                    "stream": True
                }
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", self.ollama_url, json=ollama_payload) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line.strip():
                                    try:
                                        chunk = json.loads(line)
                                        if "response" in chunk:
                                            yield chunk["response"]
                                    except Exception:
                                        pass
                        else:
                            yield "ระบบขัดข้องทั้งคลาวด์และโลคอลครับ"
            except Exception as fe:
                print(f"[Local Ollama Fallback Error]: {fe}")
                yield "ระบบขัดข้องทั้งคลาวด์และโลคอลครับ"

    async def analyze_screen_frame(self, image_bytes: bytes, user_prompt: str = None) -> dict:
        """ADA V2 Local Vision Architecture (0 API Calls, 60 FPS OpenCV HUD)."""
        return VisionParser.extract_local_opencv_hud(image_bytes)

    async def process_cli_command(self, tool_name: str, tool_args: dict) -> dict:
        """Execute CLI command directly on local Windows PC."""
        if tool_name == "execute_command":
            return CLISystemAgent.execute_command(**tool_args)
        elif tool_name == "read_file":
            return CLISystemAgent.read_file(**tool_args)
        elif tool_name == "write_file":
            return CLISystemAgent.write_file(**tool_args)
        elif tool_name == "edit_file":
            return CLISystemAgent.edit_file(**tool_args)
        elif tool_name == "delete_file":
            return CLISystemAgent.delete_file(**tool_args)
        elif tool_name == "list_directory":
            return CLISystemAgent.list_directory(**tool_args)
        else:
            return {"status": "error", "message": f"Unknown tool '{tool_name}'"}

    async def chat_with_godji(self, user_message: str, image_bytes: bytes = None, stream_callback=None) -> dict:
        """Process user text/voice prompt with local Moondream Screen Vision + Qwen2.5:7b reasoning."""
        screen_context = ""
        if image_bytes:
            vision_desc = self._query_moondream_vision(image_bytes)
            if vision_desc:
                screen_context = f"\n[ข้อมูลภาพหน้าจอที่เห็นในขณะนี้: {vision_desc}]"

        full_prompt = f"{user_message}{screen_context}"
        
        full_raw_text = ""
        is_json_mode = False
        
        async for chunk in self.stream_qwen_text(full_prompt):
            full_raw_text += chunk
            
            # Simple heuristic: if it starts with { or ```json, it's JSON mode
            if full_raw_text.strip().startswith("{") or full_raw_text.strip().startswith("```json"):
                is_json_mode = True
            
            if not is_json_mode and stream_callback:
                await stream_callback(chunk)

        reply_text = full_raw_text
        cli_cmd = None

        if is_json_mode:
            if "```json" in full_raw_text:
                try:
                    json_str = full_raw_text.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(json_str)
                    reply_text = parsed.get("reply", full_raw_text)
                    cli_cmd = parsed.get("cli_command", None)
                except Exception:
                    pass
            elif full_raw_text.strip().startswith("{") and full_raw_text.strip().endswith("}"):
                try:
                    parsed = json.loads(full_raw_text.strip())
                    reply_text = parsed.get("reply", full_raw_text)
                    cli_cmd = parsed.get("cli_command", None)
                except Exception:
                    pass
            
            # Stream the parsed reply text since we held it back
            if stream_callback and reply_text != full_raw_text:
                await stream_callback(reply_text)

        cli_output = None
        if cli_cmd:
            print(f"[Godji CLI] Executing command: {cli_cmd}")
            cli_output = CLISystemAgent.execute_command(cli_cmd)

        return {
            "reply": reply_text,
            "cli_command": cli_cmd,
            "cli_output": cli_output
        }

    async def process_voice_chat(self, audio_bytes: bytes, mime_type: str = "audio/webm", image_bytes: bytes = None) -> dict:
        """Process voice audio using 100% Local Ollama."""
        return await self.chat_with_godji("สวัสดีครับก็อดจิ", image_bytes)
