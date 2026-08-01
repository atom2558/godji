import os
import base64
import json
import asyncio
from PIL import Image
import io
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY
from app.cli_tools import CLISystemAgent, CLI_TOOLS_DECLARATIONS
from app.vision_parser import VisionParser

class GeminiAssistantClient:
    """Gemini Assistant Client for AI Godji."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY is not configured!")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

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

    async def analyze_screen_frame(self, image_bytes: bytes, user_prompt: str = None) -> dict:
        """Process a screen frame and optional user prompt, returning HUD drawing data and assistant text."""
        if not self.client:
            return {
                "subtitles": "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ในไฟล์ .env ก่อนเริ่มใช้งานครับ!",
                "bounding_boxes": [],
                "lead_dots": [],
                "arrows": []
            }

        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            prompt_text = user_prompt or (
                "โปรดวิเคราะห์ภาพหน้าจอนี้อย่างรวดเร็ว หากเห็นเป้าหมาย/คู่ต่อสู้/ปุ่มสำคัญ ให้ระบุพิกัด Bounding Box (ymin, xmin, ymax, xmax สเกล 0-1000), "
                "จุดยิงดัก (lead_dots), และทิศทาง (arrows) ในรูปแบบ JSON พร้อมข้อความ Subtitle คำอธิบาย"
            )

            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[prompt_text, image],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.4,
                )
            )

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
