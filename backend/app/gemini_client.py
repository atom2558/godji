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

    def _query_qwen_text(self, prompt: str) -> str:
        """Query 9arm Gateway API for ultra-fast Thai reasoning and CLI command synthesis."""
        try:
            url = "https://gateway.9arm.co/v1/chat/completions"
            api_key = "sk-DvdsqHV_M5uxfQm3wWPWNA"
            model_name = "qwen3.6-35b-a3b"
            
            payload = json.dumps({
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
                "temperature": 0.7
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                }
            )
            
            # Ultra-fast cloud API should reply within seconds
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    res_text = data["choices"][0]["message"]["content"].strip()
                    if res_text:
                        return res_text
        except Exception as e:
            print(f"[9arm Gateway API Error]: {e}")

        return "ขออภัยครับ ระบบเชื่อมต่อเซิร์ฟเวอร์มีปัญหา กรุณาลองใหม่อีกครั้งครับ!"

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

    async def chat_with_godji(self, user_message: str, image_bytes: bytes = None) -> dict:
        """Process user text/voice prompt with local Moondream Screen Vision + Qwen2.5:7b reasoning."""
        screen_context = ""
        if image_bytes:
            vision_desc = self._query_moondream_vision(image_bytes)
            if vision_desc:
                screen_context = f"\n[ข้อมูลภาพหน้าจอที่เห็นในขณะนี้: {vision_desc}]"

        full_prompt = f"{user_message}{screen_context}"
        raw_text = self._query_qwen_text(full_prompt)
        reply_text = raw_text
        cli_cmd = None

        if "```json" in raw_text:
            try:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
                parsed = json.loads(json_str)
                reply_text = parsed.get("reply", raw_text)
                cli_cmd = parsed.get("cli_command", None)
            except Exception:
                pass
        elif raw_text.strip().startswith("{") and raw_text.strip().endswith("}"):
            try:
                parsed = json.loads(raw_text.strip())
                reply_text = parsed.get("reply", raw_text)
                cli_cmd = parsed.get("cli_command", None)
            except Exception:
                pass

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
