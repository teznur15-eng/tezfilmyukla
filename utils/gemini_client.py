import os
import logging
import aiohttp
from utils.database import get_setting

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

async def ask_gemini(prompt: str, system_instruction: str = None) -> str:
    """
    Queries the Gemini 2.5 Flash model asynchronously.
    """
    api_key = get_setting("scout_gemini_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY/scout_gemini_key is not configured.")
        return ""

    url = f"{GEMINI_API_URL}?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_instruction}
            ]
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    logger.error(f"Gemini API returned error {resp.status}: {err_text}")
                    return ""
                
                res_json = await resp.json()
                try:
                    text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip()
                except (KeyError, IndexError) as parse_err:
                    logger.error(f"Failed to parse Gemini response: {parse_err}. Response JSON: {res_json}")
                    return ""
    except Exception as e:
        logger.error(f"Error querying Gemini API: {e}")
        return ""
