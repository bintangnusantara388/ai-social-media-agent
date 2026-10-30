"""
Image Rendering Engine (Supports 4:5 [1080x1350] and 1:1 [1080x1080])
Renders educational print content and Digital Wedding Invitations (Undangan Digital)
Integrated with Phono Print official branding & real invitation mockups from E:\\UNDANGAN DIGITAL.
"""

import os
import time
import random
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from config import Config, BASE_DIR, TEMPLATES_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "phono_print_logo_clean.png"
INVITATIONS_DIR = ASSETS_DIR / "invitations"


def get_logo_base64() -> str:
    """Reads the logo file and returns base64 encoded string for HTML embedding."""
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def get_invitation_mockup() -> tuple:
    """Returns (Path, base64_str) of an invitation mockup."""
    candidates = []
    if INVITATIONS_DIR.exists():
        candidates.extend(list(INVITATIONS_DIR.glob("*.png")) + list(INVITATIONS_DIR.glob("*.jpg")))
    
    # Also check E:\ drive if local candidates empty
    if not candidates:
        e_dir = Path(r"E:\UNDANGAN DIGITAL\Undangan Website No Label")
        if e_dir.exists():
            candidates.extend(list(e_dir.glob("*.png")) + list(e_dir.glob("*.jpg")))

    if candidates:
        chosen = random.choice(candidates)
        try:
            with open(chosen, "rb") as f:
                return chosen, base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return None, ""


class ImageGenerator:
    """Renders social media banner images (Percetakan & Undangan Digital)."""

    def __init__(self):
        self.jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    def render(
        self,
        content_data: Dict[str, Any],
        output_filename: Optional[str] = None,
        aspect_ratio: Optional[str] = None
    ) -> str:
        ratio = aspect_ratio or Config.POST_ASPECT_RATIO or "4:5"
        timestamp = int(time.time())

        category = content_data.get("category", "Edukasi Teknis")
        is_digital_invitation = "undangan" in category.lower() or "wedding" in category.lower()

        is_promo = "promo" in category.lower() or "promo" in content_data.get("visual_headline", "").lower() or content_data.get("theme") == "promo"
        is_cultivare = content_data.get("account") == "cultivare" or "cultivare" in category.lower() or "headline_en" in content_data

        if not output_filename:
            if is_cultivare:
                prefix = "cultivare_4x5"
            elif is_promo:
                prefix = "promo_4x5" if ratio == "4:5" else "promo_1x1"
            elif is_digital_invitation:
                prefix = "wedding_4x5" if ratio == "4:5" else "wedding_1x1"
            else:
                prefix = "feed_4x5" if ratio == "4:5" else "feed_1x1"
            output_filename = f"{prefix}_{timestamp}.jpg"

        output_path = OUTPUT_DIR / output_filename
        logo_b64 = get_logo_base64()
        mockup_path, mockup_b64 = get_invitation_mockup()

        headline = content_data.get("visual_headline", "Undangan Digital Elegan")
        words = headline.split()
        if len(words) > 2:
            hl_html = " ".join(words[:-2]) + f" <span class='highlight-yellow'>{words[-2]}</span> <span class='highlight-red'>{words[-1]}</span>"
        else:
            hl_html = f"<span class='highlight-yellow'>{headline}</span>"

        context = {
            "brand_name": Config.BRAND_NAME,
            "brand_tagline": Config.BRAND_TAGLINE,
            "brand_handle": Config.BRAND_HANDLE,
            "category": category.upper(),
            "visual_headline": headline,
            "visual_headline_html": hl_html,
            "visual_subtext": content_data.get("visual_subtext", "Pilihan tema adat & modern, RSVP, maps, dan musik romantis."),
            "series_number": f"{time.strftime('%y%m')}.{time.strftime('%d')}",
            "logo_base64": logo_b64,
            "mockup_base64": mockup_b64,
            "aspect_ratio": ratio,
            "is_digital_invitation": is_digital_invitation,
            "mockup_path": str(mockup_path) if mockup_path else ""
        }

        is_promo = "promo" in category.lower() or "promo" in headline.lower() or content_data.get("theme") == "promo"

        context.update({
            "height": 1350 if ratio == "4:5" else 1080,
            "promo_subline": content_data.get("promo_subline", "SPESIAL BULAN INI"),
            "discount_percent": content_data.get("discount_percent", "22%"),
            "strike_price": content_data.get("strike_price", "90K"),
            "promo_price": content_data.get("promo_price", "70K")
        })

        # Select template
        if is_cultivare:
            template_name = "banner_cultivare.html"
            dimensions = (1080, 1350)
            hl_raw = content_data.get("headline_en", content_data.get("visual_headline", "Growth is not about speed. It is about roots."))
            if "." in hl_raw:
                parts = hl_raw.split(".", 1)
                hl_html = f"{parts[0]}. <span class='highlight-green'>{parts[1].strip()}</span>"
            else:
                words = hl_raw.split()
                if len(words) > 3:
                    hl_html = " ".join(words[:-3]) + f" <span class='highlight-green'>{' '.join(words[-3:])}</span>"
                else:
                    hl_html = f"<span class='highlight-green'>{hl_raw}</span>"

            context.update({
                "brand_name": "Cultivare",
                "brand_handle": "@cultivaree_",
                "headline_html": hl_html,
                "headline_en": content_data.get("headline_en", hl_raw),
                "headline_id": content_data.get("headline_id", ""),
                "subtext_en": content_data.get("subtext_en", "Sustainable brand value is never built overnight."),
                "subtext_id": content_data.get("subtext_id", "Fondasi strategi yang mengakar adalah pembeda antara tren sesaat dan bisnis abadi."),
                "pill_cta": content_data.get("pill_cta", "lets to connect"),
                "edition_label": f"GLOBAL INSIGHT • {time.strftime('%Y')}",
            })
        elif is_promo:
            template_name = "banner_promo_kekinian.html"
            dimensions = (1080, 1350) if ratio == "4:5" else (1080, 1080)
        elif is_digital_invitation and ratio == "4:5":
            template_name = "banner_undangan_digital.html"
            dimensions = (1080, 1350)
        elif ratio == "4:5":
            template_name = "banner_4x5.html"
            dimensions = (1080, 1350)
        else:
            template_name = "banner.html"
            dimensions = (1080, 1080)


        # Attempt Playwright first
        try:
            rendered_file = self._render_with_playwright(template_name, context, output_path, dimensions)
            logger.info(f"Successfully rendered image with Playwright ({template_name}): {rendered_file}")
            return str(rendered_file)
        except Exception as e:
            logger.warning(f"Playwright rendering failed or not installed ({e}). Switching to Pillow engine...")
            rendered_file = self._render_with_pillow(context, output_path, dimensions)
            logger.info(f"Successfully rendered image with Pillow fallback: {rendered_file}")
            return str(rendered_file)

    def _render_with_playwright(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: Path,
        dimensions: tuple
    ) -> Path:
        from playwright.sync_api import sync_playwright

        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context)

        temp_html_path = OUTPUT_DIR / f"temp_{int(time.time())}.html"
        temp_html_path.write_text(html_content, encoding="utf-8")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": dimensions[0], "height": dimensions[1]}, device_scale_factor=1)
                page.goto(temp_html_path.as_uri(), wait_until="networkidle")
                page.wait_for_timeout(1000)
                page.screenshot(path=str(output_path), quality=95, type="jpeg")
                browser.close()
            return output_path
        finally:
            if temp_html_path.exists():
                try:
                    temp_html_path.unlink()
                except Exception:
                    pass

    def _render_with_pillow(self, context: Dict[str, Any], output_path: Path, dimensions: tuple) -> Path:
        """
        Pure Python Pillow fallback creating high-fidelity graphic banner.
        Supports both Dark Tech Print style and Warm Amber/Sunset Wedding style.
        """
        from PIL import Image, ImageDraw, ImageFont

        width, height = dimensions
        is_wedding = context.get("is_digital_invitation", False)

        def get_font(size: int, bold: bool = False):
            font_candidates = [
                "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            ]
            for font_file in font_candidates:
                if os.path.exists(font_file):
                    try:
                        return ImageFont.truetype(font_file, size)
                    except Exception:
                        pass
            return ImageFont.load_default()

        # ==================== WEDDING THEME (UNDANGAN DIGITAL) ====================
        if is_wedding:
            # Gradient: Warm Amber to Crimson Gold
            img = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(img)

            # Draw vertical gradient
            for y in range(height):
                factor = y / height
                r = int(245 * (1 - factor) + 90 * factor)
                g = int(140 * (1 - factor) + 15 * factor)
                b = int(10 * (1 - factor) + 5 * factor)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Header: Logo Card
            if LOGO_PATH.exists():
                logo_raw = Image.open(LOGO_PATH).convert("RGBA")
                scale = 48.0 / logo_raw.height
                logo_w = int(logo_raw.width * scale)
                logo_resized = logo_raw.resize((logo_w, 48), Image.Resampling.LANCZOS)
                draw.rounded_rectangle([(80, 65), (80 + logo_w + 36, 131)], radius=14, fill="#FFFFFF")
                img.paste(logo_resized, (98, 74), logo_resized)

            # Top Badge
            draw.rounded_rectangle([(width - 410, 68), (width - 80, 122)], radius=25, fill="#3E1004", outline="#FFD54F", width=2)
            draw.text((width - 385, 82), "👑 DIGITAL INVITATION #1", fill="#FFD54F", font=get_font(18, bold=True))

            # Edition Tag
            draw.text((80, 220), "WEDDING & CELEBRATION SERIES // PHONO PRINT", fill="#FFF9C4", font=get_font(16, bold=True))

            # Headline Wrapping
            headline_text = context["visual_headline"]
            words = headline_text.split()
            lines, cur_line = [], []
            for w in words:
                cur_line.append(w)
                if len(" ".join(cur_line)) > 18:
                    lines.append(" ".join(cur_line))
                    cur_line = []
            if cur_line:
                lines.append(" ".join(cur_line))

            y_offset = 270
            font_headline = get_font(56, bold=True)
            for i, line in enumerate(lines[:3]):
                color = "#FFEB3B" if i == len(lines[:3]) - 1 else "#FFFFFF"
                draw.text((80, y_offset), line, fill=color, font=font_headline)
                y_offset += 75

            # Mockup Center Stage
            y_stage = max(y_offset + 30, 520)
            stage_h = 360
            draw.rounded_rectangle([(80, y_stage), (width - 80, y_stage + stage_h)], radius=20, fill="#2A0B03", outline="#D97706", width=2)

            # Paste Mockup if available
            mockup_path_str = context.get("mockup_path", "")
            if mockup_path_str and os.path.exists(mockup_path_str):
                try:
                    mock_img = Image.open(mockup_path_str).convert("RGB")
                    # Resize to fit frame (460x260)
                    mock_resized = mock_img.resize((480, 270), Image.Resampling.LANCZOS)
                    img.paste(mock_resized, (110, y_stage + 45))
                except Exception as e:
                    logger.warning(f"Could not paste mockup image: {e}")

            # Feature list on the right side of the stage
            fx = 620
            fy = y_stage + 50
            features = [
                "✓ Navigasi Google Maps",
                "✓ Amplop Digital & QRIS",
                "✓ Backsound Musik",
                "✓ Galeri Foto Prewed"
            ]
            for feat in features:
                draw.text((fx, fy), feat, fill="#FFFFFF", font=get_font(20, bold=True))
                fy += 45

            # Price pill
            draw.rounded_rectangle([(fx, fy + 10), (width - 110, fy + 65)], radius=12, fill="#D50000", outline="#FF8A80", width=1)
            draw.text((fx + 18, fy + 24), "MULAI 70K // BELI 5 GRATIS 1", fill="#FFFDE7", font=get_font(16, bold=True))

            # Subtext Card
            y_sub = y_stage + stage_h + 30
            draw.rounded_rectangle([(80, y_sub), (width - 80, y_sub + 140)], radius=14, fill="#3E1004", outline="#FFB800", width=1)
            draw.rounded_rectangle([(80, y_sub), (92, y_sub + 140)], radius=4, fill="#FFEB3B")

            sub_words = context["visual_subtext"].split()
            sub_lines, cur_sub = [], []
            for sw in sub_words:
                cur_sub.append(sw)
                if len(" ".join(cur_sub)) > 42:
                    sub_lines.append(" ".join(cur_sub))
                    cur_sub = []
            if cur_sub:
                sub_lines.append(" ".join(cur_sub))

            sy = y_sub + 28
            for sline in sub_lines[:2]:
                draw.text((120, sy), sline, fill="#FFFDE7", font=get_font(24))
                sy += 38

            # Footer
            y_footer = height - 120
            draw.line([(80, y_footer), (width - 80, y_footer)], fill="#D97706", width=2)
            # WhatsApp Button
            draw.rounded_rectangle([(80, y_footer + 20), (450, y_footer + 85)], radius=30, fill="#FFFFFF")
            draw.text((110, y_footer + 36), "💬 PESAN: 085141316787", fill="#C62828", font=get_font(18, bold=True))

            draw.text((width - 340, y_footer + 28), context["brand_handle"], fill="#FFFFFF", font=get_font(20, bold=True))
            draw.text((width - 340, y_footer + 56), "DIGITAL INVITATION TEGAL", fill="#FFEB3B", font=get_font(14, bold=True))

            img.save(str(output_path), "JPEG", quality=95)
            return output_path

        # ==================== DEFAULT TECH PRINT THEME ====================
        img = Image.new("RGB", (width, height), color="#0B0E14")
        draw = ImageDraw.Draw(img)

        # Background Grid Pattern
        for x in range(0, width, 60):
            draw.line([(x, 0), (x, height)], fill="#111622", width=1)
        for y in range(0, height, 60):
            draw.line([(0, y), (width, y)], fill="#111622", width=1)

        # Top CMYK Calibration Bar
        cmyk_colors = ["#00E5FF", "#FF007F", "#FFD600", "#262B35"]
        bar_w = width // 4
        for i, col in enumerate(cmyk_colors):
            draw.rectangle([(i * bar_w, 0), ((i + 1) * bar_w, 8)], fill=col)

        # Corner Crop Marks
        crop_color = "#475569"
        draw.line([(30, 30), (70, 30)], fill=crop_color, width=2)
        draw.line([(30, 30), (30, 70)], fill=crop_color, width=2)
        draw.line([(width - 30, 30), (width - 70, 30)], fill=crop_color, width=2)
        draw.line([(width - 30, 30), (width - 30, 70)], fill=crop_color, width=2)
        draw.line([(30, height - 30), (70, height - 30)], fill=crop_color, width=2)
        draw.line([(30, height - 30), (30, height - 70)], fill=crop_color, width=2)
        draw.line([(width - 30, height - 30), (width - 70, height - 30)], fill=crop_color, width=2)
        draw.line([(width - 30, height - 30), (width - 30, height - 70)], fill=crop_color, width=2)

        # Header: Logo Card
        if LOGO_PATH.exists():
            logo_raw = Image.open(LOGO_PATH).convert("RGBA")
            scale = 48.0 / logo_raw.height
            logo_w = int(logo_raw.width * scale)
            logo_resized = logo_raw.resize((logo_w, 48), Image.Resampling.LANCZOS)
            card_w = logo_w + 36
            draw.rounded_rectangle([(80, 65), (80 + card_w, 131)], radius=14, fill="#FFFFFF")
            img.paste(logo_resized, (98, 74), logo_resized)

        # Category Badge
        badge_text = f"• {context['category']}"
        draw.rounded_rectangle([(width - 360, 68), (width - 80, 122)], radius=25, fill="#240D15", outline="#C00A27", width=2)
        draw.text((width - 335, 82), badge_text, fill="#FF4D6D", font=get_font(18, bold=True))
        draw.text((width - 310, 132), "TEGAL - CREATIVE PRINT LAB", fill="#94A3B8", font=get_font(12, bold=True))

        # Middle Section
        draw.text((80, 250), f"PRINTING PRO-SERIES // VOL. {context['series_number']}", fill="#FFB800", font=get_font(18, bold=True))

        headline_text = context["visual_headline"]
        words = headline_text.split()
        lines, cur_line = [], []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 18:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))

        y_offset = 310
        font_headline = get_font(58, bold=True)
        for i, line in enumerate(lines[:3]):
            color = "#FFB800" if i == len(lines[:3]) - 1 else "#FFFFFF"
            draw.text((80, y_offset), line, fill=color, font=font_headline)
            y_offset += 80

        # Subtext Card
        y_card = y_offset + 40
        card_height = 180 if height > 1100 else 160
        draw.rounded_rectangle([(80, y_card), (width - 80, y_card + card_height)], radius=16, fill="#131B2A", outline="#1E293B", width=2)
        draw.rounded_rectangle([(80, y_card), (92, y_card + card_height)], radius=4, fill="#C00A27")

        sub_words = context["visual_subtext"].split()
        sub_lines, cur_sub = [], []
        for sw in sub_words:
            cur_sub.append(sw)
            if len(" ".join(cur_sub)) > 42:
                sub_lines.append(" ".join(cur_sub))
                cur_sub = []
        if cur_sub:
            sub_lines.append(" ".join(cur_sub))

        sub_y = y_card + 35
        for sline in sub_lines[:3]:
            draw.text((120, sub_y), sline, fill="#CBD5E1", font=get_font(28))
            sub_y += 44

        # 4:5 Checklist
        if height >= 1350:
            y_checks = y_card + card_height + 40
            checklist_items = [
                ("✓ Color Mode: CMYK", "Cegah warna kusam saat dicetak"),
                ("✓ Resolusi 300 DPI", "Hasil cetak tajam & tidak pecah"),
                ("✓ Bleed Area 3mm", "Aman dari pisau potong mesin"),
                ("✓ Format PDF/X-1a", "Standar industri percetakan modern")
            ]

            grid_col_w = (width - 160 - 20) // 2
            for idx, (title, desc) in enumerate(checklist_items):
                col = idx % 2
                row = idx // 2
                gx = 80 + col * (grid_col_w + 20)
                gy = y_checks + row * 95

                draw.rounded_rectangle([(gx, gy), (gx + grid_col_w, gy + 80)], radius=14, fill="#141923", outline="#222B3B", width=1)
                draw.text((gx + 20, gy + 16), title, fill="#FFFFFF", font=get_font(18, bold=True))
                draw.text((gx + 20, gy + 44), desc, fill="#94A3B8", font=get_font(14))

        # Footer
        y_footer = height - 120
        draw.line([(80, y_footer), (width - 80, y_footer)], fill="#1E293B", width=2)

        draw.rounded_rectangle([(80, y_footer + 25), (420, y_footer + 85)], radius=30, fill="#C00A27")
        draw.text((115, y_footer + 40), "SWIPE UNTUK SOLUSI ➔", fill="#FFFFFF", font=get_font(18, bold=True))

        draw.text((width - 340, y_footer + 30), context["brand_handle"], fill="#FFFFFF", font=get_font(20, bold=True))
        draw.text((width - 340, y_footer + 58), "OFFSET & DIGITAL TEGAL", fill="#FFB800", font=get_font(14, bold=True))

        img.save(str(output_path), "JPEG", quality=95)
        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = ImageGenerator()
    test_wedding = {
        "category": "Undangan Digital Website",
        "visual_headline": "Mau Wedding Vibes Elegan & Classy?",
        "visual_subtext": "Tampilan website modern, fitur RSVP, Google Maps, dan musik romantis langsung di smartphone tamu."
    }
    f = gen.render(test_wedding, aspect_ratio="4:5")
    print(f"Rendered test wedding banner: {f}")
