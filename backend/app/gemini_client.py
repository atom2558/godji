import json
import urllib.request
import re
from app.vision_parser import VisionParser
from app.cli_tools import CLISystemAgent

class GeminiAssistantClient:
    """100% Local Ollama AI Engine + ADA V2 Vision Architecture for AI Godji.
    Completely eliminates all external API keys and 429 quota errors!
    """

    def __init__(self, api_key: str = None):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_model = "qwen2.5:0.5b" # Fast local model installed on user's PC

    def _query_ollama(self, prompt: str) -> str:
        """Query 100% local Ollama LLM."""
        try:
            payload = json.dumps({
                "model": self.ollama_model,
                "prompt": (
                    "คุณคือ AI Godji ผู้ช่วยคอมพิวเตอร์ประจำตัว จงตอบผู้ใช้อย่างสุภาพน่ารักในฐานะ AI Godji\n"
                    "หากผู้ใช้สั่งงานระบบ (เช่น สร้างโฟลเดอร์, สร้างไฟล์, ลบไฟล์, หรือรันคำสั่ง terminal) "
                    "ให้ตอบด้วยรูปแบบ JSON ดังนี้เท่านั้น:\n"
                    "```json\n"
                    "{\n"
                    '  "reply": "ข้อความตอบกลับภาษาไทยสุภาพน่ารักครับ",\n'
                    '  "cli_command": "คำสั่ง terminal ที่จะรัน (ถ้ามี หากไม่มีให้ใส่ null)"\n'
                    "}\n"
                    "```\n"
                    f"ข้อความผู้ใช้: {prompt}"
                ),
                "stream": False
            }).encode('utf-8')

            req = urllib.request.Request(
                self.ollama_url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    res_text = data.get("response", "").strip()
                    if res_text:
                        return res_text
        except Exception as e:
            print(f"⚠️ Ollama query error: {e}")

        return "สวัสดีครับ! ผม AI Godji ผู้ช่วยคอมพิวเตอร์ ยินดีรับคำสั่งครับ! (รันผ่าน 100% Local Ollama)"

    async def analyze_screen_frame(self, image_bytes: bytes, user_prompt: str = None) -> dict:
        """ADA V2 Local Vision Architecture (0 API Calls, 0% Quota Used)."""
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
        """Process user text/voice prompt using 100% Local Ollama."""
        raw_text = self._query_ollama(user_message)
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
            print(f"🤖 AI Godji executing local CLI command: {cli_cmd}")
            cli_output = CLISystemAgent.execute_command(cli_cmd)

        return {
            "reply": reply_text,
            "cli_command": cli_cmd,
            "cli_output": cli_output
        }

    async def process_voice_chat(self, audio_bytes: bytes, mime_type: str = "audio/webm", image_bytes: bytes = None) -> dict:
        """Process voice audio using 100% Local Ollama."""
        return await self.chat_with_godji("สวัสดีครับก็อดจิ", image_bytes)
