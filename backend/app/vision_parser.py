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
            return True  # Fallback to process frame on any error

    @staticmethod
    def parse_gemini_hud_response(raw_text: str) -> Dict[str, Any]:
        """Extract structured JSON for overlay HUD (Bounding boxes, lead dots, arrows, subtitles)
        from Gemini response text.
        """
        hud_data = {
            "bounding_boxes": [],  # list of {label, ymin, xmin, ymax, xmax, color}
            "lead_dots": [],       # list of {label, y, x, color}
            "arrows": [],          # list of {from_x, from_y, to_x, to_y, label}
            "subtitles": ""        # string subtitle
        }

        if not raw_text:
            return hud_data

        # Try extracting JSON code block first
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

        # Text fallback parse if model responds with natural text
        hud_data["subtitles"] = raw_text.strip()
        return hud_data
