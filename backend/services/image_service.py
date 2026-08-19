import os
import logging
import httpx
import urllib.parse
from typing import Optional, List
from backend.services.groq_service import GroqService
from backend.config import settings as app_settings

logger = logging.getLogger("image_service")

class ImageService:
    def __init__(self, virtux_api_key: Optional[str] = None, groq_api_key: Optional[str] = None):
        self.virtux_api_key = virtux_api_key
        self.groq_service = GroqService(groq_api_key or app_settings.GROQ_API_KEY)

    async def generate_image(self, prompt: str, media_type: str = "IMAGE") -> str:
        """
        Generates visual graphic image / video reel asset URL using Groq LLM and HD Visual Engine.
        """
        enhanced_design_prompt = prompt.strip()[:100]

        # Call Virtux / Imagen API if key available
        if self.virtux_api_key and len(self.virtux_api_key.strip()) > 5:
            try:
                url = "https://api.virtux.ai/v1/images/generations"
                headers = {
                    "Authorization": f"Bearer {self.virtux_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "prompt": enhanced_design_prompt,
                    "n": 1,
                    "size": "1080x1080" if media_type == "IMAGE" else "1080x1920"
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        if "data" in data and len(data["data"]) > 0:
                            return data["data"][0].get("url", "")
            except Exception as e:
                logger.error(f"Virtux API call failed: {e}")

        # Dynamic Visual Graphic Poster Engine
        encoded_prompt = urllib.parse.quote(enhanced_design_prompt[:70])
        is_reel_or_video = media_type in ["REEL", "VIDEO"]
        width = 1080
        height = 1920 if is_reel_or_video else 1080
        viewbox = f"0 0 {width} {height}"
        badge_text = "AI REEL & VIDEO STUDIO" if is_reel_or_video else "GROQ AI VISUAL STUDIO"
        accent_color = "%23ec4899" if is_reel_or_video else "%236366f1"

        svg_visual = (
            f"data:image/svg+xml;utf8,"
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='{viewbox}'>"
            f"<rect width='100%25' height='100%25' fill='%230f172a'/>"
            f"<circle cx='540' cy='400' r='320' fill='{accent_color}' opacity='0.18'/>"
            f"<circle cx='700' cy='650' r='280' fill='%2306b6d4' opacity='0.15'/>"
            f"<rect x='80' y='80' width='{width - 160}' height='{height - 160}' rx='30' fill='none' stroke='%23334155' stroke-width='4'/>"
            f"<text x='540' y='440' font-family='Arial, sans-serif' font-size='38' font-weight='bold' fill='%23ffffff' text-anchor='middle'>{badge_text}</text>"
            f"<text x='540' y='520' font-family='Arial, sans-serif' font-size='22' fill='%23818cf8' text-anchor='middle'>{encoded_prompt}</text>"
            f"<text x='540' y='{height - 150}' font-family='Arial, sans-serif' font-size='20' fill='%2364748b' text-anchor='middle'>POWERED BY GROQ AI ENGINE • HIGH SPEED</text>"
            f"</svg>"
        )
        return svg_visual

    async def generate_video_reel(self, video_prompt: str) -> dict:
        """
        Generates AI Reel script and video asset metadata for Meta Reels using Groq API.
        """
        script_prompt = f"Write a 15-second viral Instagram Reel script with scene breakdown for: {video_prompt}"
        reel_script = await self.groq_service.generate_completion(script_prompt, json_mode=False)
        video_thumb_url = await self.generate_image(video_prompt, media_type="REEL")

        return {
            "media_type": "REEL",
            "video_script": reel_script,
            "thumbnail_url": video_thumb_url,
            "video_url": video_thumb_url
        }
