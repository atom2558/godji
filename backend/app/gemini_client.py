import os
import base64
import json
import asyncio
from PIL import Image
import io
import google.generativeai as genai
from app.config import GEMINI_API_KEY
from app.cli_tools import CLISystemAgent, CLI_TOOLS_DECLARATIONS
from app.vision_parser import VisionParser

class GeminiAssistantClient:
    """Gemini Assistant Client for AI Godji."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.system_prompt = """คุณคือ "AI Godji" (เอไอ ก็อดจิ) ผู้ช่วยอัจฉริยะแบบภาพและเสียงแบบเรียลไทม์ที่น่ารัก ฉลาด รอบรู้ และขี้เล่น
หน้าที่ของคุณ:
1. วิเคราะห์ภาพหน้าจอคอมพิวเตอร์ของผู้ใช้อยู่ตลอดเวลา
2. หากเห็นเป้าหมาย, ศัตรู, หรือปุ่ม/ตำแหน่งสำคัญบนหน้าจอ ให้ระบุพิกัดในรูปแบบ JSON สำหรับวาดบน Transparent HUD Overlay:
```json
{
  "bounding_boxes": [
    {"label": "คู่ต่อสู้", "ymin": 200, "xmin": 300, "ymax": 500, "xmax": 450, "color": "orange"}
  ],
  "lead_dots": [
    {"label": "จุดยิงดัก", "y": 300, "x": 520, "color": "blue"}
  ],
  "arrows": [
    {"from_x": 400, "from_y": 250, "to_x": 500, "to_y": 250, "label": "คู่ต่อสู้ไปทางขวา"}
  ],
  "subtitles": "พบเป้าหมายเคลื่อนที่ไปทางขวา เล็งจุดยิงดักข้างหน้าได้เลยครับ!"
}
```
3. สามารถใช้งาน CLI Tools ในการอ่านไฟล์, แก้ไขไฟล์ (edit_file), ลบไฟล์ (delete_file) หรือรันคำสั่ง Terminal บนคอมพิวเตอร์ของผู้ใช้ได้ตามสั่ง
4. พูดจาด้วยน้ำเสียงเป็นมิตร สุภาพ มีหางเสียง "ครับ" แบบ AI Godji
"""
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY is not configured!")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self.system_prompt
            )

    async def analyze_screen_frame(self, image_bytes: bytes, user_prompt: str = None) -> dict:
        """Process a screen frame and optional user prompt, returning HUD drawing data and assistant text."""
        if not self.model:
            return {
                "subtitles": "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ใน Render / .env ก่อนเริ่มใช้งานครับ!",
                "bounding_boxes": [],
                "lead_dots": [],
                "arrows": []
            }

        try:
            image = Image.open(io.BytesIO(image_bytes))

            prompt_text = user_prompt or (
                "โปรดวิเคราะห์ภาพหน้าจอนี้อย่างรวดเร็ว หากเห็นเป้าหมาย/คู่ต่อสู้/ปุ่มสำคัญ ให้ระบุพิกัด Bounding Box (ymin, xmin, ymax, xmax สเกล 0-1000), "
                "จุดยิงดัก (lead_dots), และทิศทาง (arrows) ในรูปแบบ JSON พร้อมข้อความ Subtitle คำอธิบาย"
            )

            # Generate content using Gemini with automatic multi-model fallback on 429
            response = self._generate_content_with_fallback([prompt_text, image])

            raw_text = response.text or ""
            parsed_hud = VisionParser.parse_gemini_hud_response(raw_text)
            return parsed_hud

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {
                "subtitles": f"⚠️ เกิดข้อผิดพลาดในการวิเคราะห์ภาพ: {str(e)}",
                "bounding_boxes": [],
                "lead_dots": [],
                "arrows": []
            }

    def _generate_content_with_fallback(self, contents: list):
        """Helper to generate content, automatically trying alternative models if 429 Quota is hit."""
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.5-pro"
        ]
        
        last_exception = None
        for model_name in models_to_try:
            try:
                m = genai.GenerativeModel(model_name=model_name, system_instruction=self.system_prompt)
                res = m.generate_content(contents)
                return res
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    print(f"⚠️ Model '{model_name}' hit 429 rate limit! Auto-switching to next model...")
                    last_exception = e
                    continue
                else:
                    raise e
                    
        if last_exception:
            print("⚠️ All Gemini models hit 429/quota limits! Auto-routing to Local Ollama...")
            # Create a mock response object wrapping Ollama local response
            ollama_reply = self._query_ollama_local(contents)
            class OllamaResponseMock:
                def __init__(self, text):
                    self.text = text
            return OllamaResponseMock(ollama_reply)

    def _query_ollama_local(self, contents: list) -> str:
        """Call local Ollama when Gemini API quota is fully exhausted."""
        prompt_str = "สวัสดีครับ"
        for item in contents:
            if isinstance(item, str):
                prompt_str = item
                break

        try:
            url = "http://localhost:11434/api/generate"
            payload = json.dumps({
                "model": "qwen2.5:0.5b",
                "prompt": f"คุณคือ AI Godji ผู้ช่วยคอมพิวเตอร์ จงตอบคำถามนี้เป็นภาษาไทยอย่างสุภาพ: {prompt_str}",
                "stream": False
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    return res_data.get("response", "สวัสดีครับ ผม AI Godji ครับ (ตอบผ่าน Local Ollama)")
        except Exception as e:
            print(f"Ollama local fallback failed: {e}")

        return "⚠️ โควต้าฟรีของ Gemini API เต็มประจำวันแล้วครับ (สามารถสร้าง API Key ใหม่ใน Google AI Studio หรือผูกบัตรแบบ Pay-as-you-go เพื่อเปิดความเร็วเต็มสปีดได้ครับ)"

    async def process_cli_command(self, tool_name: str, tool_args: dict) -> dict:
        """Handle CLI tool calls executed by AI Godji."""
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
        """Process direct user chat/voice message, execute CLI action if needed, and return response text."""
        if not self.model:
            return {
                "reply": "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ก่อนเริ่มสนทนาครับ!",
                "cli_output": None
            }

        try:
            prompt_content = []
            sys_msg = (
                f"ผู้ใช้ส่งข้อความถึงคุณว่า: '{user_message}'\n"
                "โปรดตอบกลับผู้ใช้อย่างสุภาพน่ารักในฐานะ AI Godji และหากผู้ใช้สั่งงานระบบ (เช่น สร้างโฟลเดอร์, สร้างไฟล์, ลบไฟล์, หรือรันคำสั่ง terminal) "
                "ให้ตอบกลับด้วยรูปแบบ JSON ดังนี้เท่านั้น:\n"
                "```json\n"
                "{\n"
                '  "reply": "คำตอบภาษาไทยสุภาพน่ารักที่มีหางเสียงครับ",\n'
                '  "cli_command": "คำสั่ง terminal ที่จะสั่งรัน (หากสั่งงานระบบ เช่น สร้างไฟล์/โฟลเดอร์ หากไม่มีให้เป็น null)"\n'
                "}\n"
                "```"
            )
            prompt_content.append(sys_msg)

            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes))
                prompt_content.append(image)

            response = self._generate_content_with_fallback(prompt_content)
            raw_text = response.text or ""

            reply_text = raw_text
            cli_cmd = None

            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
                try:
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
                print(f"🤖 AI Godji executing command from chat: {cli_cmd}")
                cli_output = CLISystemAgent.execute_command(cli_cmd)

            return {
                "reply": reply_text,
                "cli_command": cli_cmd,
                "cli_output": cli_output
            }

        except Exception as e:
            print(f"Error in chat_with_godji: {e}")
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                print("⚠️ Gemini 429 encountered in chat_with_godji -> Routing to local Ollama")
                return {
                    "reply": self._query_ollama_local([user_message]),
                    "cli_output": None
                }
            return {
                "reply": f"⚠️ เกิดข้อผิดพลาดในการสนทนา: {err_msg}",
                "cli_output": None
            }

    async def process_voice_chat(self, audio_bytes: bytes, mime_type: str = "audio/webm", image_bytes: bytes = None) -> dict:
        """Process direct audio recording from microphone using Gemini Multimodal capability."""
        if not self.model:
            return {
                "reply": "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ก่อนเริ่มสนทนาครับ!",
                "cli_output": None
            }

        try:
            prompt_content = []
            sys_msg = (
                "ฟังเสียงที่ผู้ใช้พูดในไฟล์เสียงนี้ ตอบคำถามอย่างสุภาพน่ารัก และทำตามคำสั่ง:\n"
                "หากผู้ใช้สั่งให้ควบคุมระบบ (เช่น สร้างโฟลเดอร์, สร้างไฟล์, ลบไฟล์, หรือรันคำสั่ง Windows/Linux) "
                "ให้ตอบกลับด้วยรูปแบบ JSON ดังนี้เท่านั้น:\n"
                "```json\n"
                "{\n"
                '  "reply": "คำตอบภาษาไทยสุภาพน่ารักที่มีหางเสียงครับ",\n'
                '  "cli_command": "คำสั่ง terminal ที่จะสั่งรัน (หากสั่งงานระบบ เช่น สร้างไฟล์/โฟลเดอร์ หากไม่มีให้เป็น null)"\n'
                "}\n"
                "```"
            )
            prompt_content.append(sys_msg)
            
            # Attach audio inline
            prompt_content.append({
                "mime_type": mime_type,
                "data": audio_bytes
            })

            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes))
                prompt_content.append(image)

            response = self._generate_content_with_fallback(prompt_content)
            raw_text = response.text or ""

            reply_text = raw_text
            cli_cmd = None

            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
                try:
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
                print(f"🤖 AI Godji executing command from voice chat: {cli_cmd}")
                cli_output = CLISystemAgent.execute_command(cli_cmd)

            return {
                "reply": reply_text,
                "cli_command": cli_cmd,
                "cli_output": cli_output
            }

        except Exception as e:
            print(f"Error in process_voice_chat: {e}")
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                print("⚠️ Gemini 429 encountered in process_voice_chat -> Routing to local Ollama")
                return {
                    "reply": self._query_ollama_local(["โปรดตอบกลับผู้ใช้อย่างสุภาพน่ารักในฐานะ AI Godji ครับ"]),
                    "cli_output": None
                }
            return {
                "reply": f"⚠️ เกิดข้อผิดพลาดในการฟังเสียง: {err_msg}",
                "cli_output": None
            }


