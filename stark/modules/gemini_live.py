"""
STARK Gemini Live Integration
──────────────────────────────
Uses Google Gemini Live API for real-time voice conversation.
This is the key differentiator for the Gemini Live Agent Challenge.
"""

import asyncio
import base64
import json
import os
import threading
import pyaudio
import requests

# Gemini Live WebSocket endpoint
GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

SYSTEM_INSTRUCTION = """You are STARK, a powerful personal AI Operating System.
You control the user's computer, answer questions, navigate maps, send messages.
Be concise, warm, and helpful. Address user as Sir."""


class GeminiLiveAgent:
    """
    Real-time voice agent using Gemini Live API.
    Streams audio in → gets streaming audio back.
    """

    def __init__(self, api_key: str, voice_module=None):
        self._api_key   = api_key
        self._voice     = voice_module
        self._running   = False
        self._ws        = None

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key != "YOUR_GEMINI_API_KEY_HERE")

    def ask_gemini(self, question: str, context: str = "") -> str:
        """
        Send question to Gemini and get response.
        Uses Gemini 1.5 Flash for fast responses.
        """
        if not self.is_available():
            return ""

        try:
            prompt = question
            if context:
                prompt = f"Context: {context}\n\nQuestion: {question}"

            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"gemini-1.5-flash:generateContent?key={self._api_key}")

            resp = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                }
            }, timeout=15)

            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[Gemini Live] {e}")
        return ""

    def identify_image(self, image_bytes: bytes, question: str = "What is in this image? Identify any people, objects, text.") -> str:
        """Use Gemini vision to identify images."""
        if not self.is_available():
            return ""
        try:
            img_b64 = base64.b64encode(image_bytes).decode()
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"gemini-1.5-flash:generateContent?key={self._api_key}")
            resp = requests.post(url, json={
                "contents": [{"parts": [
                    {"text": question},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]}]
            }, timeout=15)
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[Gemini Vision] {e}")
        return ""

    def analyze_screen(self, screenshot_bytes: bytes) -> str:
        """Analyze screen content with Gemini vision."""
        return self.identify_image(
            screenshot_bytes,
            "Describe what is on this screen. Identify any people, apps, text content, "
            "or anything notable. Be specific with names if recognizable."
        )

    def stream_answer(self, question: str, on_chunk=None) -> str:
        """Stream response from Gemini — shows text as it generates."""
        if not self.is_available():
            return ""
        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"gemini-1.5-flash:streamGenerateContent?key={self._api_key}&alt=sse")
            resp = requests.post(url, json={
                "contents": [{"parts": [{"text": question}]}],
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            }, stream=True, timeout=30)

            full_text = ""
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    try:
                        data = json.loads(line[6:])
                        chunk = data["candidates"][0]["content"]["parts"][0].get("text","")
                        if chunk:
                            full_text += chunk
                            if on_chunk:
                                on_chunk(chunk)
                    except Exception:
                        pass
            return full_text
        except Exception as e:
            print(f"[Gemini Stream] {e}")
        return ""