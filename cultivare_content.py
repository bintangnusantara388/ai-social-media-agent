"""
Cultivare Content Engine (Bilingual EN + ID)
Generates high-level analytical content covering:
- Global Business & Macro Economy
- Culture & Modern Consumer Dynamics
- Hot World News & Market Shifts
- Strategic Brand Development ("Roots over speed", Clarity, Structure, Growth)
"""

import json
import logging
import random
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests

from config import Config

logger = logging.getLogger(__name__)

CULTIVARE_PILLARS = [
    {
        "category": "Global Business Trends",
        "topics": [
            "AI Disruption: How Generative AI is Reshaping Enterprise Margin Economics",
            "The Death of the Middle Brand: Why Premium and Budget are Winning While Average Dies",
            "Why Silicon Valley Giants are Cutting Bureaucracy to Protect Startup Agility",
            "The Subscription Fatigue Era: Why Bundled Value is the Next Battleground",
            "The Rise of Solopreneurs: How 1-Person Billion Dollar Companies Are Becoming Real"
        ]
    },
    {
        "category": "Culture & Economy",
        "topics": [
            "Loud Budgeting: Why Frugality Became the Ultimate Gen-Z Luxury Status Symbol",
            "The Experience Economy: Why Young Consumers Buy Flights and Concerts Over Houses",
            "Quiet Luxury and Cultural Fatigue: The Rejection of Obvious Logos in Modern Wealth",
            "Work Culture Shift: The Tension Between Remote Autonomy and Corporate Control",
            "Coffee Shop Economics: How Cafe Culture Became the Living Room of Remote Workers"
        ]
    },
    {
        "category": "Hot World News & Macro",
        "topics": [
            "Central Banks, Interest Rate Cycles, and the Looming Liquidity Squeeze in Emerging Markets",
            "Semiconductor Geopolitics: Why Microchips Are the Crude Oil of the 21st Century",
            "Global Supply Chain De-risking: How Southeast Asia Became the Primary Manufacturing Winner",
            "The Energy Transition Dilemma: balancing AI Datacenter Power Demand with Carbon Targets",
            "Currency Dynamics: The Digital Yuan, Dollar Hegemony, and the Multi-Polar Financial Order"
        ]
    },
    {
        "category": "Strategic Brand Development",
        "topics": [
            "Growth is Not About Speed, It is About Roots: The Fallacy of Premature Scaling",
            "We Don't Build Brands to be Seen, We Build Them to Grow: The Power of Intentional Positioning",
            "Brand Clarity Over Marketing Noise: Why Clear Narrative Trumps Huge Ad Spend",
            "The Moat Principle: How Authentic Brand Philosophy Protects Pricing Power",
            "Building With Intention: Why Structure and Culture Are Your Real Competitive Advantage"
        ]
    },
    {
        "category": "Market Teardowns & Case Studies",
        "topics": [
            "Nvidia's 3 Trillion Dollar Playbook: How Hardware Monopoly Built an Unassailable Ecosystem",
            "LVMH's Art of Desirability: Why Scarcity and Heritage Defy Macro Recessions",
            "Nike vs On Running: How Agile Challenger Brands Exploit Giants That Lose Cultural Edge",
            "Apple's Privacy Engine: Turning Consumer Protection Into the Ultimate Closed Wall",
            "Costco's Negative Margin Secret: How Membership Loyalty Generates 70% of Profits"
        ]
    }
]

CULTIVARE_SYSTEM_PROMPT = """You are a Senior Strategic Brand Consultant, Macroeconomic Analyst, and Cultural Strategist for 'Cultivare Collective' (@cultivaree_).

Brand Identity:
- Name: Cultivare Collective (@cultivaree_)
- Bio: Strategic Brand Development | Building brands to grow — not just be seen | Clarity. Structure. Growth. | Build with intention.
- Editorial Tone: Sophisticated, insightful, intellectual, minimal, punchy, thought-provoking. Think Bloomberg Opinion meets Monocle, HBR, and Kinfolk.
- Core Philosophy: "Growth is not about speed. It is about roots." We prioritize sustainable long-term value, clarity, structural moats, and deep cultural resonance over vanity metrics.

LANGUAGE REQUIREMENT: STRICTLY BILINGUAL (English + Bahasa Indonesia)
The target audience consists of forward-thinking founders, executives, investors, and creative directors across Southeast Asia and globally.

JSON OUTPUT SPECIFICATION:
Output strictly pure valid JSON without markdown wrapping (```json), without opening or trailing commentary.

Required JSON Structure:
{
  "category": "Global Business Trends / Culture & Economy / Hot World News & Macro / Strategic Brand Development / Market Teardowns & Case Studies",
  "headline_en": "Punchy editorial headline in English (maximum 10 words, strong assertion or philosophical contrast)",
  "headline_id": "Headline translation in Bahasa Indonesia (ringkas dan tajam)",
  "subtext_en": "Insightful analytical thesis in English (maximum 22 words)",
  "subtext_id": "Ringkasan tesis mendalam dalam Bahasa Indonesia (maksimal 22 kata)",
  "pill_cta": "lets to connect / innovate with ease / read the brief / build with intention",
  "caption": "Full structured bilingual caption containing:
🇬🇧 [THE BRIEFING]: 2-3 concise paragraphs of sharp global economic / strategic analysis in English with strategic takeaway.
🇮🇩 [PERSPEKTIF]: 2-3 paragraf ulasan kontekstual dalam Bahasa Indonesia yang mengaitkan fenomena ini dengan realitas bisnis, investasi, dan brand di Indonesia.
💬 [THE INQUIRY]: 1 thought-provoking question for the comment section.
#️⃣ [TAGS]: 10-15 relevant hashtags (#cultivare #globaleconomy #strategicbranding #businesstrends #macroeconomics #cultureandeconomy #branddevelopment #growthstrategy)"
}
"""


class CultivareContentGenerator:
    """Generates bilingual strategic business and economy content for Cultivare."""

    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.api_key = Config.GEMINI_API_KEY
        self.model = "gemini-flash-lite-latest"

    def generate(self, category_override: Optional[str] = None, topic_hint: Optional[str] = None) -> Dict[str, Any]:
        """Generates structured bilingual content for Cultivare."""
        if category_override:
            pillar = next((p for p in CULTIVARE_PILLARS if category_override.lower() in p["category"].lower()), None)
            if not pillar:
                pillar = random.choice(CULTIVARE_PILLARS)
        else:
            pillar = random.choice(CULTIVARE_PILLARS)

        selected_category = pillar["category"]
        selected_topic = topic_hint if topic_hint else random.choice(pillar["topics"])

        user_prompt = f"""Generate an editorial briefing for Cultivare Collective:
Category: {selected_category}
Topic: {selected_topic}

Make the headline philosophical yet commercially razor-sharp (e.g. 'Growth is not about speed. It is about roots').
Deliver the output as pure valid JSON following the schema strictly."""

        logger.info(f"Cultivare Generating topic: '{selected_topic}' under category: '{selected_category}'")

        if self.api_key and not self.api_key.startswith("AIzaSyYour"):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "systemInstruction": {"parts": [{"text": CULTIVARE_SYSTEM_PROMPT}]},
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                cleaned = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
                parsed = json.loads(cleaned)
                return parsed
            except Exception as e:
                logger.warning(f"Cultivare Gemini call failed ({e}). Using editorial fallback.")

        # High-fidelity editorial fallback if network/API drops
        return {
            "category": selected_category,
            "headline_en": "Growth is not about speed. It is about roots.",
            "headline_id": "Pertumbuhan bukan soal kecepatan. Ini soal akar.",
            "subtext_en": "Sustainable brand value is never built overnight. When market volatility strikes, only deeply rooted strategies survive.",
            "subtext_id": "Nilai brand jangka panjang tidak lahir dalam semalam. Fondasi strategi yang mengakar adalah pembeda antara tren sesaat dan bisnis abadi.",
            "pill_cta": "build with intention",
            "caption": (
                "Growth is not about speed. It is about roots.\n\n"
                "🇬🇧 [THE BRIEFING]\n"
                "In an era obsessed with overnight metrics and hyper-scaling, founders frequently mistake velocity for viability. "
                "The real competitive moat is never built on ad-spend arbitrage—it is rooted in structural clarity, distinct narrative positioning, and operational discipline.\n\n"
                "When macro liquidity tightens, organizations with deep cultural roots and unassailable customer trust thrive, while superficial growth engines evaporate.\n\n"
                "🇮🇩 [PERSPEKTIF]\n"
                "Banyak bisnis terjebak mengejar angka pertumbuhan instan tanpa membangun fondasi operasional dan diferensiasi brand yang solid. "
                "Saat dinamika ekonomi global bergejolak, brand yang memiliki 'akar'—identitas yang jelas, efisiensi modal, dan loyalitas komunitas—akan selalu bertahan lebih lama dibanding mereka yang hanya mengandalkan bakar uang.\n\n"
                "💬 [THE INQUIRY]\n"
                "What is the single most critical 'root' in your brand architecture today: Your product moat, your cultural relevance, or your capital discipline?\n\n"
                "#cultivare #strategicbranding #globaleconomy #businesstrends #macroeconomics #cultureandeconomy #brandstrategy #growthmindset #businessclarity"
            )
        }
