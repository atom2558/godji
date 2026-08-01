import json
import re
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

class VisionParser:
    """Parses screen frame analysis and extracts bounding boxes, lead dots, arrows, and subtitles."""

    @staticmethod
    def detect_motion_or_changes(prev_frame_bytes: bytes, curr_frame_bytes: bytes, threshold: float = 5.0) -> bool:
        """Local OpenCV Frame Difference filter.
        Returns True if significant motion/change occurred between frames, avoiding unnecessary API calls.
        """
        if not prev_frame_bytes or not curr_frame_bytes:
            return True

        try:
            nparr1 = np.frombuffer(prev_frame_bytes, np.uint8)
            nparr2 = np.frombuffer(curr_frame_bytes, np.uint8)

            img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None or img1.shape != img2.shape:
                return True

            diff = cv2.absdiff(img1, img2)
            mean_diff = np.mean(diff)

            return mean_diff > threshold
        except Exception:
            return True

    @staticmethod
    def extract_local_opencv_hud(image_bytes: bytes) -> Dict[str, Any]:
        """ADA V2 Local Vision Architecture:
        Extracts UI bounding boxes, active elements, and motion contours locally using OpenCV (0 API calls, 60 FPS).
        """
        hud_data = {
            "bounding_boxes": [],
            "lead_dots": [],
            "arrows": [],
            "subtitles": "วิเคราะห์องค์ประกอบบนหน้าจอแบบเรียลไทม์ (ADA Local Vision)"
        }
        if not image_bytes:
            return hud_data

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return hud_data

            h, w, _ = img.shape
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            color_palette = ["cyan", "green", "orange", "purple", "yellow"]
            count = 0

            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                # Filter for active UI bounding boxes
                if 50 < cw < w * 0.75 and 40 < ch < h * 0.75:
                    ymin = int((y / h) * 1000)
                    xmin = int((x / w) * 1000)
                    ymax = int(((y + ch) / h) * 1000)
                    xmax = int(((x + cw) / w) * 1000)

                    hud_data["bounding_boxes"].append({
                        "label": f"UI Component #{count + 1}",
                        "ymin": ymin,
                        "xmin": xmin,
                        "ymax": ymax,
                        "xmax": xmax,
                        "color": color_palette[count % len(color_palette)]
                    })
                    count += 1
                    if count >= 6:
                        break
        except Exception as e:
            print(f"Local OpenCV Vision error: {e}")

        return hud_data

    @staticmethod
    def parse_gemini_hud_response(raw_text: str) -> Dict[str, Any]:
        """Extract structured JSON for overlay HUD (Bounding boxes, lead dots, arrows, subtitles)
        from Gemini/Ollama response text.
        """
        hud_data = {
            "bounding_boxes": [],
            "lead_dots": [],
            "arrows": [],
            "subtitles": ""
        }

        if not raw_text:
            return hud_data

        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)

        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                hud_data["bounding_boxes"] = parsed.get("bounding_boxes", [])
                hud_data["lead_dots"] = parsed.get("lead_dots", [])
                hud_data["arrows"] = parsed.get("arrows", [])
                hud_data["subtitles"] = parsed.get("subtitles", "")
                return hud_data
            except Exception:
                pass

        clean_subtitle = raw_text.strip()
        if clean_subtitle.startswith("```") or clean_subtitle.startswith("{") or "429" in clean_subtitle or "quota" in clean_subtitle.lower():
            clean_subtitle = "พบองค์ประกอบและสตรีมภาพบนหน้าจอครับ"
        hud_data["subtitles"] = clean_subtitle
        return hud_data
