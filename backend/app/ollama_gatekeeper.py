import urllib.request
import json
import asyncio

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:0.5b"

class OllamaGatekeeper:
    """Uses local Ollama to check if user prompt is meant for AI Godji before calling Gemini API (Token Saver)."""
    
    WAKE_KEYWORDS = ["godji", "ก็อดจิ", "กอดจิ", "เอไอ", "god", "ก๊อดจิ"]

    @classmethod
    def _query_ollama_sync(cls, text_prompt: str) -> bool:
        prompt_lower = text_prompt.lower()
        if any(kw in prompt_lower for kw in cls.WAKE_KEYWORDS):
            print(f"[Ollama Gatekeeper] Wake word matched for '{text_prompt}'")
            return True

        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": (
                f"Analyse if this Thai/English text is a question or command directed at an AI assistant called Godji: '{text_prompt}'\n"
                "Answer strictly with YES or NO."
            ),
            "stream": False
        }).encode('utf-8')

        req = urllib.request.Request(
            OLLAMA_API_URL,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, timeout=2.5) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    res_text = res_data.get("response", "").strip().upper()
                    if "YES" in res_text:
                        print(f"[Ollama Gatekeeper] Ollama intent=YES")
                        return True
        except Exception as e:
            print(f"[Ollama Gatekeeper] Check offline/skipped ({e})")

        print(f"[Ollama Gatekeeper] Ignored '{text_prompt}'")
        return False

    @classmethod
    async def should_forward_to_gemini(cls, text_prompt: str) -> bool:
        if not text_prompt or not text_prompt.strip():
            return False
        return await asyncio.to_thread(cls._query_ollama_sync, text_prompt)
