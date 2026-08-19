import os
import json
import logging
import httpx
from typing import Optional, Dict, Any
from backend.config import settings as app_settings

logger = logging.getLogger("groq_service")

class GroqService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or app_settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.fallback_models = [
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768",
            "llama3-70b-8192"
        ]

    async def generate_completion(self, prompt: str, json_mode: bool = True) -> str:
        """
        Calls Groq API with automatic model fallbacks and structured JSON output.
        """
        if not self.api_key:
            logger.warning("Groq API key missing. Using fallback master engine.")
            return self._generate_fallback(prompt, json_mode)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        system_instruction = (
            "You are the Ultimate Single Master AI Autonomous Agent for Facebook & Instagram Social Media Growth. "
            "Respond strictly in valid JSON format."
            if json_mode else
            "You are the Master AI Autonomous Agent for Facebook Social Media Growth."
        )

        for model in self.fallback_models:
            payload: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            if json_mode and "llama-3" in model:
                payload["response_format"] = {"type": "json_object"}

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(self.endpoint, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"Groq API call success with model '{model}'.")
                        return content
                    else:
                        logger.warning(f"Groq model '{model}' returned status {res.status_code}: {res.text[:120]}")
            except Exception as e:
                logger.error(f"Error calling Groq API model '{model}': {e}")

        logger.warning("All Groq API models exhausted. Returning intelligent fallback response.")
        return self._generate_fallback(prompt, json_mode)

    def _generate_fallback(self, prompt: str, json_mode: bool) -> str:
        if json_mode:
            return json.dumps({
                "trend_analysis": "Biotech & Organic Growth Revolution",
                "strategy_focus": "50% Educational Value, 30% Engagement, 20% Product Showcase",
                "title": "Stop Posting Manually: The Master AI Autonomous Revolution",
                "hook": "What if ONE Single Master AI Agent handled your entire Facebook page 24/7?",
                "caption": "Managing social media manually takes hours of planning, writing, and graphic design. With our Single Master AI Agent, everything from trend research to visual design and publishing happens autonomously.",
                "cta": "Click the link in bio to experience 100% autonomous page growth!",
                "hashtags": "#AIGrowth #SocialMediaManager #AutomatedMarketing #MasterAI #AutonomousAgent",
                "media_type": "IMAGE",
                "content_angle": "EDUCATIONAL",
                "image_prompt": "Futuristic dark mode master AI core visual with glowing neon blue and purple nodes"
            })
        return "Master AI Autonomous Agent processing complete."
