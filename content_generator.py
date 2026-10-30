"""
Content Generator Module (Content Engine)
Uses LLM API (Google Gemini or OpenAI) to generate structured printing education content.
Output strictly adheres to JSON format without markdown wraps.
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

# Daftar 4 Pilar Konten Percetakan
CONTENT_PILLARS = [
    {
        "category": "Edukasi Teknis",
        "topics": [
            "Perbedaan CMYK vs RGB dan Mengapa Layar HP Menipu Mata",
            "Pentingnya Resolusi 300 DPI untuk Menghindari Cetakan Pecah",
            "Mengenal Bleed dan Safe Zone 3mm agar Desain Tidak Terpotong",
            "Format File Standar Percetakan: PDF/X-1a vs TIFF vs Vector EPS",
            "Mencegah Masalah Overprint dan Trapping pada Teks Hitam Pekat (Rich Black)",
            "Raster Image Processor (RIP): Bagaimana File Digital Diubah Menjadi Titik Cetak"
        ]
    },
    {
        "category": "Material & Kertas",
        "topics": [
            "Memilih Kertas: Perbedaan Karakteristik Art Paper vs Art Carton",
            "Keistimewaan Kertas Ivory: Pilihan Utama Kemasan Makanan & Kosmetik",
            "Mengenal Kertas Kraft Coklat & Corrugated Box untuk Kemasan Eco-friendly",
            "Panduan Gramatur Kertas (GSM): Dari Brosur 120 GSM hingga Box 350 GSM",
            "Mengenal Fancy Paper: Kertas Bertekstur untuk Kartu Nama & Undangan Mewah",
            "Arah Serat Kertas (Grain Direction): Kenapa Buku Sering Menggelombang"
        ]
    },
    {
        "category": "Finishing Pasca Cetak",
        "topics": [
            "Laminasi Doff vs Glossy: Mana yang Lebih Tepat untuk Produk Anda?",
            "Efek Mewah Spot UV: Cara Menonjolkan Elemen Desain dengan Kilau Glaze",
            "Hot Stamping Foil: Menambahkan Aksen Emas & Silver Metalik Mengkilap",
            "Emboss dan Deboss: Memberi Tekstur Timbul 3D pada Kemasan",
            "Teknik Pond & Die-Cut: Membuat Pola Kemasan Custom Tanpa Batas",
            "Penjilidan Buku: Jilid Kawat (Saddle Stitch) vs Lem Panas (Perfect Binding)"
        ]
    },
    {
        "category": "Tips Bisnis & Efisiensi",
        "topics": [
            "Optimasi Layout Cetak (Gang Run): Trik Hemat Ongkos Produksi Massal",
            "Tips Packaging Khusus UMKM: Cara Tampil Mewah dengan Budget Minimum",
            "Penyebab Utama Hasil Cetak Belang/Banding dan Cara Mencegahnya",
            "Checklist Pra-Cetak (Pre-flight): 5 Hal Wajib Dicek Sebelum Kirim File ke Vendor",
            "Digital Offset (Indigo) vs Offset Konvensional: Kapan Harus Memilih Mana?",
            "Solusi Mengatasi Perbedaan Warna Monitor Designer dengan Mesin Cetak Industri"
        ]
    },
    {
        "category": "Undangan Digital Website",
        "topics": [
            "Undangan Website vs Cetak: Solusi Hybrid Pengantin Modern Kekinian",
            "5 Fitur Canggih Undangan Website: RSVP, Google Maps, Amplop QRIS & Musik",
            "Cara Sebar Ratusan Undangan Tanpa Boncos Ongkir Lewat Undangan Website",
            "Tema Wedding Vibes Elegan & Classy: Kesan Mewah Sejak Klik Pertama",
            "Paket Undangan Website Phono Print: Mulai 80 Ribu & Promo Beli 5 Gratis 1"
        ]
    },
    {
        "category": "Undangan Digital Video",
        "topics": [
            "Undangan Video Animasi Adat: Jawa, Sunda, Minang, Bali, hingga Sumatra",
            "Undangan Video Aqiqah & Khitan: Cara Praktis & Estetik Berbagi Kabar Bahagia",
            "Save The Date Video: Teaser Pernikahan Sinematik untuk Story & Reels",
            "Kelebihan Undangan Video: Praktis Dibagikan Lewat WhatsApp Hanya 1 Menit",
            "Paket Express Undangan Digital Phono Print: Kilat Siap Sebar"
        ]
    },
    {
        "category": "Promo Spesial Undangan",
        "topics": [
            "PROMO SPESIAL UNDANGAN DIGITAL: Diskon 22% Cuma 70K dari 90K Free Buku Tamu & Musik",
            "Flash Sale Undangan Website: Cuma 70 Ribu Sudah Termasuk RSVP, Maps & Lagu Romantis",
            "Promo Spesial Pengantin Baru: Undangan Digital Kekinian Tampil Mewah Tanpa Boncos",
            "Promo Terbatas Phono Print: Undangan Digital Responsive HP Siap Sebar Kilat",
            "Spesial Diskon 22%: Undangan Website Eksklusif & Buku Tamu Digital Interaktif"
        ]
    }
]


@dataclass
class GeneratedContent:
    category: str
    visual_headline: str
    visual_subtext: str
    caption: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "visual_headline": self.visual_headline,
            "visual_subtext": self.visual_subtext,
            "caption": self.caption
        }


SYSTEM_PROMPT = """Bertindaklah sebagai Senior Printing Specialist, Digital Wedding Invitation Consultant, dan Content Creator profesional untuk brand PHONO PRINT (Tegal - Creative).

Brand: PHONO PRINT (Tegal - Creative) | Handle: @phono.print_tegal | WhatsApp Pemesanan: 085141316787

Layanan Utama Phono Print:
1. Layanan Cetak Fisik: Offset printing, digital printing, packaging kemasan, brosur, kartu nama, buku, kalender, finishing mewah (doff, glossy, spot UV, hotprint emas).
2. Layanan Undangan Digital:
   - Undangan Website: Fitur RSVP otomatis, navigasi Google Maps presisi, amplop digital/QRIS, galeri foto prewed, background music romantis, hitung mundur (countdown). Harga mulai Rp 80.000 (Paket Reguler) & Rp 150.000 (Paket Express). Promo: Setiap pembelian 5 undangan website GRATIS 1.
   - Undangan Video Animasi: Tema adat lengkap (Jawa, Sunda, Minang, Bali, Sumatra), tema Modern Classy, Aqiqah, dan Khitan. Harga mulai Rp 70.000 - Rp 90.000.

Pilar Konten:
1. Edukasi Teknis Cetak (CMYK vs RGB, 300 DPI, bleed & safe zone, format file cetak PDF/X)
2. Material & Kertas (Art Paper, Art Carton, Ivory, Fancy Paper, Kraft, Corrugated, GSM)
3. Finishing Pasca Cetak (Doff vs Glossy, Spot UV, Foil/Hotprint, Emboss/Deboss, Die-cut/Pond)
4. Tips Bisnis & Efisiensi Cetak (Gang run printing, packaging UMKM, cara mencegah hasil cetak belang)
5. Undangan Digital Website (Fitur canggih, efisiensi budget, kemudahan sebar tamu, tema estetik)
6. Undangan Digital Video (Tema adat, video Save The Date, undangan aqiqah/khitan, paket kilat)
7. Promo Spesial Undangan (Promo kekinian diskon 22% dari 90K jadi 70K, free buku tamu & musik, proses cepat 1-2 hari)

PEDOMAN GAYA BAHASA:
- Edukatif, ramah, meyakinkan, praktis, dan profesional.
- Caption Instagram harus terstruktur rapi:
  1. Hook menarik di baris pertama (menarik perhatian calon pengantin, designer, atau UMKM).
  2. Paragraf inti dengan penjelasan bernilai tinggi & solusi nyata.
  3. Call-to-Action (CTA) jelas dengan menyertakan kontak WhatsApp Phono Print (085141316787) atau ajakan simpan/share.
  4. 10 - 15 hashtag relevan bertema percetakan atau undangan digital (#undangandigital #undanganwebsite #undanganvideo #undangantegal #percetakantegal #phonoprint #weddinginvitation dll).

ATURAN OUTPUT:
Keluarkan HANYA string JSON valid murni tanpa format markdown codeblock (` ```json `), tanpa teks pembuka atau penutup.

Format JSON yang diwajibkan:
{
  "category": "Edukasi Teknis / Material & Kertas / Finishing Pasca Cetak / Tips Bisnis & Efisiensi / Undangan Digital Website / Undangan Digital Video / Promo Spesial Undangan",
  "visual_headline": "Teks judul untuk banner gambar (maksimal 7 kata)",
  "visual_subtext": "Penjelasan inti untuk banner (maksimal 15 kata)",
  "caption": "Teks caption lengkap berisi hook, isi penjelasan, Call-to-Action (CTA WhatsApp 085141316787), dan 10-15 hashtag relevan"
}
"""


class ContentGenerator:
    """Orchestrates content generation using the configured LLM."""

    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        logger.info(f"Initialized ContentGenerator with provider: {self.provider}")

    def generate(self, category_override: Optional[str] = None, topic_hint: Optional[str] = None) -> GeneratedContent:
        """
        Generate educational print content adhering strictly to the schema.
        """
        # Tentukan topik dan kategori
        if category_override:
            pillar = next((p for p in CONTENT_PILLARS if p["category"].lower() == category_override.lower()), None)
            if not pillar:
                pillar = random.choice(CONTENT_PILLARS)
        else:
            pillar = random.choice(CONTENT_PILLARS)

        selected_category = pillar["category"]
        selected_topic = topic_hint if topic_hint else random.choice(pillar["topics"])

        user_prompt = f"""Buatkan konten edukasi Instagram untuk:
Kategori: {selected_category}
Topik Spesifik: {selected_topic}

Pastikan:
1. 'visual_headline': Maksimal 7 kata, ringkas, menarik, dan berbobot.
2. 'visual_subtext': Maksimal 15 kata, rangkuman inti pesan banner.
3. 'caption': Berisi hook, penjelasan mendalam, CTA, dan 10-15 hashtag.
Keluarkan HANYA JSON murni!"""

        logger.info(f"Generating content for topic: '{selected_topic}' under category: '{selected_category}'")

        # Check for empty or placeholder API keys (e.g. from .env.example)
        has_real_gemini = Config.GEMINI_API_KEY and "YourGeminiApiKeyHere" not in Config.GEMINI_API_KEY and not Config.GEMINI_API_KEY.startswith("AIzaSyYour")
        has_real_openai = Config.OPENAI_API_KEY and "YourOpenAiApiKeyHere" not in Config.OPENAI_API_KEY

        if not has_real_gemini and not has_real_openai:
            logger.warning("No valid LLM API key detected in .env! Generating educational preview content for Phono Print...")
            return self._generate_fallback_content(selected_category, selected_topic)

        try:
            if self.provider == "gemini":
                raw_response = self._call_gemini(user_prompt)
            elif self.provider == "openai":
                raw_response = self._call_openai(user_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            return self._parse_and_validate(raw_response, fallback_category=selected_category)
        except Exception as e:
            logger.warning(f"LLM API call failed ({e}). Using educational fallback content...")
            return self._generate_fallback_content(selected_category, selected_topic)

    def _generate_fallback_content(self, category: str, topic: str) -> GeneratedContent:
        """High quality educational fallback content generator for Phono Print."""
        fallback_map = {
            "Edukasi Teknis": {
                "headline": "CMYK vs RGB: Jangan Salah Format File",
                "subtext": "File RGB pada mesin offset memicu pergeseran warna drastis dan hasil kusam.",
                "hook": "Kenapa warna desain di layar HP sering beda jauh saat dicetak? 🤔👇",
                "body": (
                    "Banyak desainer pemula kaget saat hasil cetak brosur atau kemasan terlihat kusam dan gelap. "
                    "Penyebab utamanya adalah perbedaan color space:\n\n"
                    "1️⃣ RGB (Red, Green, Blue): Berbasis cahaya monitor/HP. Gamut warna lebih luas.\n"
                    "2️⃣ CMYK (Cyan, Magenta, Yellow, Key/Black): Berbasis pigmen tinta fisik pada kertas.\n\n"
                    "💡 Solusi Praktis dari Phono Print:\n"
                    "- Selalu ubah Color Mode ke CMYK sejak awal membuat dokumen di Adobe Illustrator/InDesign.\n"
                    "- Hindari warna neon/elektrik RGB di luar jangkauan gamut tinta cetak.\n"
                    "- Manfaatkan proofing warna fisik sebelum masuk proses produksi massal."
                )
            },
            "Material & Kertas": {
                "headline": "Art Paper vs Art Carton: Bedanya Apa?",
                "subtext": "Kenali perbedaan ketebalan dan karakter kertas untuk hasil cetak maksimal.",
                "hook": "Brosur kamu letoy atau kartu nama kamu kaku? Cek jenis kertasnya! 📄👇",
                "body": (
                    "Salah pilih kertas bisa bikin budget cetak boncos dan hasil tidak profesional:\n\n"
                    "1️⃣ Art Paper (85 - 150 GSM): Tipis, licin, mengkilap. Sangat ideal untuk brosur, flyer, majalah, dan isi booklet.\n"
                    "2️⃣ Art Carton (190 - 400 GSM): Tebal, kokoh, permukaan semi-glossy. Pilihan wajib kartu nama, cover buku, kalender, dan paper bag.\n\n"
                    "💡 Tips Phono Print:\n"
                    "Untuk kartu nama dan kemasan, minimal gunakan Art Carton 260 atau 310 GSM ditambah laminasi doff agar kokoh dan tahan air!"
                )
            },
            "Finishing Pasca Cetak": {
                "headline": "Spot UV & Foil: Rahasia Kemasan Mewah",
                "subtext": "Tambahkan efek kilau glaze dan foil emas untuk nilai jual produk lebih tinggi.",
                "hook": "Ingin produk UMKM kamu terlihat seperti brand internasional di rak toko? ✨👇",
                "body": (
                    "Finishing pasca cetak adalah pembeda antara cetakan standar dan cetakan premium:\n\n"
                    "1️⃣ Spot UV: Memberikan efek glossy mengkilap hanya pada area tertentu (misal: logo brand).\n"
                    "2️⃣ Hot Stamping Foil: Menempelkan lapisan foil emas/silver metalik mengkilap dengan tekanan panas.\n"
                    "3️⃣ Emboss/Deboss: Efek timbul 3D yang memberikan sensasi sentuhan mewah saat dipegang.\n\n"
                    "💡 Rekomendasi Phono Print:\n"
                    "Kombinasikan laminasi Doff hitam dengan Hot Stamping Gold Foil untuk kemasan kosmetik atau kuliner mewah!"
                )
            },
            "Tips Bisnis & Efisiensi": {
                "headline": "Trik Cetak Massal: Gang Run Printing",
                "subtext": "Gabungkan layout cetak pada satu pelat untuk pangkas biaya produksi UMKM.",
                "hook": "Mau cetak kemasan custom tapi modal pas-pasan? Ini triknya! 💡👇",
                "body": (
                    "Biaya cetak offset mahal karena pembuatan pelat cetak (CTP) dan waktu setting mesin.\n\n"
                    "Solusinya adalah teknik Gang Run (Cetak Keroyokan):\n"
                    "- Beberapa desain produk atau kemasan digabungkan dalam satu lembar plano kertas besar.\n"
                    "- Ongkos pelat dan biaya mesin dibagi rata sehingga harga per pcs jauh lebih murah.\n\n"
                    "💡 Konsultasikan layout produkmu di Phono Print Tegal untuk efisiensi produksi maksimal!"
                )
            },
            "Undangan Digital Website": {
                "headline": "Undangan Website: Gak Harus Ribet & Mahal!",
                "subtext": "Solusi praktis undang ratusan tamu dengan fitur RSVP, Maps, dan amplop digital.",
                "hook": "Lagi pusing mikirin budget cetak dan sebar undangan pernikahan? Ini solusinya! 💍👇",
                "body": (
                    "Zaman sekarang, calon pengantin modern lebih cerdas memilih Undangan Website:\n\n"
                    "✨ Fitur Premium Undangan Website Phono Print:\n"
                    "📍 Navigasi Google Maps Presisi (Tamu gak bakal tersesat)\n"
                    "💌 Amplop Digital & QRIS Langsung ke Rekening Pengantin\n"
                    "🎵 Background Music Romantis Pilihan Kamu\n"
                    "📸 Galeri Foto & Cerita Cinta (Love Story)\n"
                    "✅ Konfirmasi Kehadiran Tamu (RSVP) Otomatis\n\n"
                    "💰 Paket Hemat Phono Print:\n"
                    "- Paket Reguler: Mulai Rp 80.000\n"
                    "- Paket Express (Hitungan Jam): Rp 150.000\n"
                    "🎁 PROMO SPESIAL: Setiap pemesanan 5 undangan website, GRATIS 1!\n\n"
                    "Konsultasi tema undangan impianmu via WhatsApp: 085141316787 📲"
                )
            },
            "Undangan Digital Video": {
                "headline": "Undangan Video Animasi: Mewah & Berkesan",
                "subtext": "Bagikan momen bahagiamu lewat video animasi adat dan modern beresolusi HD.",
                "hook": "Bikin tamu undangan terkesan dalam 60 detik pertama video pernikahanmu! 🎬✨",
                "body": (
                    "Ingin sebar undangan lewat WhatsApp Story atau Instagram Reels dengan estetik?\n\n"
                    "Kelebihan Undangan Video Phono Print:\n"
                    "🏛️ Pilihan Tema Adat Lengkap: Jawa, Sunda, Minang, Bali, Sumatra, dan Modern Minimalis.\n"
                    "👶 Tersedia juga tema Aqiqah, Khitan, dan Ulang Tahun.\n"
                    "⚡ Format MP4 HD siap sebar di WA, IG Reels, dan TikTok.\n\n"
                    "🔥 Special Price mulai dari Rp 70.000 - Rp 90.000 saja!\n\n"
                    "Pesan sekarang sebelum slot produksi penuh! Hubungi WA: 085141316787 📲"
                )
            }
        }

        data = fallback_map.get(category, fallback_map["Edukasi Teknis"])

        caption = (
            f"{data['hook']}\n\n"
            f"{data['body']}\n\n"
            f"📌 Simpan postingan ini agar tidak lupa saat mengirim file ke percetakan!\n"
            f"Konsultasikan kebutuhan cetak bisnismu bersama Phono Print Tegal ✨\n\n"
            f"#edukasicetak #percetakan #cetakoffset #desaingrafis #graphicdesignindonesia "
            f"#offsetprinting #tipscetak #artpaper #percetakantegal #phonoprint #tegalcreative"
        )

        return GeneratedContent(
            category=category,
            visual_headline=data["headline"],
            visual_subtext=data["subtext"],
            caption=caption
        )



        return self._parse_and_validate(raw_response, fallback_category=selected_category)

    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API with automatic model fallback."""
        api_key = Config.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment.")

        models_to_try = [
            Config.GEMINI_MODEL or "gemini-flash-lite-latest",
            "gemini-flash-lite-latest",
            "gemini-3.8-flash",
            "gemini-flash-latest"
        ]

        # Deduplicate while preserving order
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        last_error = None
        for model in unique_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"System Instructions:\n{SYSTEM_PROMPT}\n\nTask:\n{prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "response_mime_type": "application/json"
                }
            }

            headers = {"Content-Type": "application/json"}
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        logger.info(f"Successfully generated content using Gemini model: {model}")
                        return candidates[0]["content"]["parts"][0]["text"]
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(f"Model {model} returned {resp.status_code}. Trying next model...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error calling model {model}: {e}. Trying next model...")

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API using REST endpoint."""
        api_key = Config.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured in environment.")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": Config.OPENAI_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            raise

    def _parse_and_validate(self, raw_text: str, fallback_category: str) -> GeneratedContent:
        """Clean markdown code fences, parse JSON, and enforce limits."""
        cleaned = raw_text.strip()
        # Hapus markdown code block jika model tetap menyertakannya
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as err:
            logger.error(f"JSON decode failed. Raw text:\n{raw_text}")
            # Regex fallback jika JSON terpotong sebagian
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                raise ValueError(f"Failed to parse LLM output as JSON: {err}")

        # Normalisasi dan validasi
        category = parsed.get("category", fallback_category)
        headline = parsed.get("visual_headline", "").strip()
        subtext = parsed.get("visual_subtext", "").strip()
        caption = parsed.get("caption", "").strip()

        # Word count safety trims
        headline_words = headline.split()
        if len(headline_words) > 7:
            logger.warning(f"Headline exceeded 7 words ({len(headline_words)} words). Truncating.")
            headline = " ".join(headline_words[:7])

        subtext_words = subtext.split()
        if len(subtext_words) > 15:
            logger.warning(f"Subtext exceeded 15 words ({len(subtext_words)} words). Truncating.")
            subtext = " ".join(subtext_words[:15])

        if not headline or not caption:
            raise ValueError("LLM generated empty headline or caption.")

        return GeneratedContent(
            category=category,
            visual_headline=headline,
            visual_subtext=subtext,
            caption=caption
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing ContentGenerator...")
    # Mock test or prompt test
    try:
        gen = ContentGenerator()
        print("Content Generator initialized successfully.")
    except Exception as e:
        print(f"Init notice: {e}")
