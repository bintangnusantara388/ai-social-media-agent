"""
Multi-Account Admin Web Application & Content Plan Calendar
Supports:
1. PHONO PRINT (Tegal - Creative): Printing & Digital Wedding Invitations
2. CULTIVARE COLLECTIVE (@cultivaree_): Global Business, Macro Economy, Culture & Strategic Branding
"""

import sys
import os
import json
import time
import base64
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# Windows UTF-8 console output fix for emojis
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config, BASE_DIR, STORAGE_DIR, OUTPUT_DIR, ASSETS_DIR
from content_generator import ContentGenerator, CONTENT_PILLARS
from cultivare_content import CultivareContentGenerator, CULTIVARE_PILLARS
from image_generator import ImageGenerator
from cloud_storage import CloudStorageUploader
from instagram_publisher import InstagramPublisher
from content_planner import (
    load_content_plan,
    save_content_plan,
    add_schedule_item,
    update_schedule_status,
    delete_schedule_item,
    get_default_30_day_plan,
    edit_schedule_item,
    update_account_default_time
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("AdminApp")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "storage" / "output")
)


def get_account_logo_base64(account: str = "phono_print") -> str:
    """Returns base64 encoded string for the active account's logo."""
    cfg = Config.get_account_config(account)
    logo_path = ASSETS_DIR / cfg.get("logo_file", "phono_print_logo_clean.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    # Fallback to Phono Print logo
    fallback = ASSETS_DIR / "phono_print_logo_clean.png"
    if fallback.exists():
        with open(fallback, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def get_history(account: str = "phono_print"):
    """Reads publish history JSON for the specified account."""
    hist_file = STORAGE_DIR / f"publish_history_{account}.json" if account == "cultivare" else STORAGE_DIR / "publish_history.json"
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(record: dict, account: str = "phono_print"):
    """Appends record to the specified account's publish history."""
    hist_file = STORAGE_DIR / f"publish_history_{account}.json" if account == "cultivare" else STORAGE_DIR / "publish_history.json"
    hist = get_history(account)
    hist.append(record)
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)


@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    """Serves the main Multi-Account Admin Dashboard."""
    default_acc = request.args.get("account", "phono_print")
    cfg = Config.get_account_config(default_acc)
    logo_b64 = get_account_logo_base64(default_acc)
    pillars = CULTIVARE_PILLARS if default_acc == "cultivare" else CONTENT_PILLARS

    return render_template(
        "admin_dashboard.html",
        active_account=default_acc,
        brand_name=cfg["name"],
        brand_tagline=cfg["tagline"],
        brand_handle=cfg["handle"],
        logo_base64=logo_b64,
        pillars=pillars
    )


@app.route("/api/stats")
def api_stats():
    """Returns real-time dashboard statistics and health for the requested account."""
    account = request.args.get("account", "phono_print")
    cfg = Config.get_account_config(account)
    history = get_history(account)
    calendar = load_content_plan(account)

    scheduled_count = len([c for c in calendar if c.get("status") == "scheduled"])
    published_count = len(history)

    # Health check summary
    gemini_ok = bool(Config.GEMINI_API_KEY and not Config.GEMINI_API_KEY.startswith("AIzaSyYour"))
    meta_ok = bool(cfg.get("instagram_access_token") and cfg.get("instagram_account_id"))
    cloudinary_ok = bool(Config.CLOUDINARY_CLOUD_NAME and Config.CLOUDINARY_API_KEY)

    latest_post = history[-1] if history else None

    return jsonify({
        "status": "ok",
        "account": account,
        "published_count": published_count,
        "scheduled_count": scheduled_count,
        "latest_post": latest_post,
        "brand": cfg,
        "logo_base64": get_account_logo_base64(account),
        "health": {
            "gemini_ai": {"connected": gemini_ok, "model": Config.GEMINI_MODEL},
            "meta_instagram": {
                "connected": meta_ok,
                "version": Config.GRAPH_API_VERSION,
                "account_id": cfg.get("instagram_account_id", "")
            },
            "cloudinary_cdn": {"connected": cloudinary_ok, "cloud_name": Config.CLOUDINARY_CLOUD_NAME}
        },
        "scheduler": {
            "hour": cfg["schedule_hour"],
            "minute": cfg["schedule_minute"],
            "timezone": Config.TIMEZONE,
            "default_ratio": cfg["default_ratio"]
        }
    })


@app.route("/api/calendar", methods=["GET"])
def api_get_calendar():
    """Returns the content plan calendar items for the requested account, enriched with publication history."""
    account = request.args.get("account", "phono_print")
    plan = load_content_plan(account)
    history = get_history(account)
    hist_by_link = {h.get("permalink"): h for h in history if h.get("permalink")}

    for item in plan:
        if item.get("permalink") and item["permalink"] in hist_by_link:
            h = hist_by_link[item["permalink"]]
            item["image_url"] = h.get("image_url")
            item["media_id"] = h.get("media_id")
            item["visual_headline"] = h.get("visual_headline")
            item["visual_subtext"] = h.get("visual_subtext")
            item["published_at"] = h.get("timestamp")

    return jsonify({"status": "ok", "account": account, "items": plan})


@app.route("/api/calendar/add", methods=["POST"])
def api_add_calendar_item():
    """Adds a new scheduled post to the calendar."""
    data = request.json or {}
    account = data.get("account", "phono_print")
    date = data.get("date")
    time_str = data.get("time")
    category = data.get("category", "Global Business Trends" if account == "cultivare" else "Edukasi Teknis")
    topic = data.get("topic", "")
    aspect_ratio = data.get("aspect_ratio", "4:5")
    notes = data.get("notes", "")

    if not date or not topic:
        return jsonify({"status": "error", "message": "Date and topic are required."}), 400

    new_item = add_schedule_item(date, time_str, category, topic, aspect_ratio, notes, account=account)
    return jsonify({"status": "ok", "account": account, "item": new_item})


@app.route("/api/calendar/reset-30days", methods=["POST"])
def api_reset_calendar():
    """Regenerates a fresh balanced 30-day content plan."""
    data = request.json or {}
    account = data.get("account", "phono_print")
    plan = get_default_30_day_plan(account)
    save_content_plan(plan, account)
    return jsonify({
        "status": "ok",
        "account": account,
        "items": plan,
        "message": f"Jadwal 30 hari untuk {account.replace('_', ' ').title()} berhasil diperbarui!"
    })


@app.route("/api/calendar/<item_id>", methods=["DELETE"])
def api_delete_calendar_item(item_id):
    """Deletes a schedule item."""
    account = request.args.get("account", "phono_print")
    success = delete_schedule_item(item_id, account=account)
    return jsonify({"status": "ok" if success else "not_found"})


@app.route("/api/calendar/edit", methods=["POST"])
def api_edit_calendar_item():
    """Edits an existing schedule item (date, time, category, topic, aspect_ratio)."""
    data = request.json or {}
    account = data.get("account", "phono_print")
    item_id = data.get("id")
    date = data.get("date")
    time_str = data.get("time")
    category = data.get("category")
    topic = data.get("topic")
    aspect_ratio = data.get("aspect_ratio", "4:5")
    notes = data.get("notes", "")

    if not item_id or not date or not topic:
        return jsonify({"status": "error", "message": "ID, date, dan topic wajib diisi."}), 400

    updated = edit_schedule_item(item_id, date, time_str, category, topic, aspect_ratio, notes, account=account)
    if updated:
        return jsonify({"status": "ok", "account": account, "item": updated})
    return jsonify({"status": "error", "message": "Jadwal tidak ditemukan."}), 404


@app.route("/api/settings/schedule", methods=["POST"])
def api_update_schedule_time():
    """
    Updates the daily global broadcast schedule time for the specified account.
    Also updates .env and optionally upcoming calendar items.
    """
    data = request.json or {}
    account = data.get("account", "phono_print")
    time_str = data.get("time", "").strip()
    apply_to_calendar = data.get("apply_to_calendar", True)

    if not time_str or ":" not in time_str:
        return jsonify({"status": "error", "message": "Format jam tidak valid (contoh: 09:00 atau 18:30)."}), 400

    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Jam harus 0-23 dan menit 0-59.")

        formatted_time = f"{hour:02d}:{minute:02d}"

        # 1. Update .env and Config
        if account == "cultivare":
            Config.update_env_value("CULTIVARE_SCHEDULE_HOUR", f"{hour:02d}")
            Config.update_env_value("CULTIVARE_SCHEDULE_MINUTE", f"{minute:02d}")
        else:
            Config.update_env_value("SCHEDULE_HOUR", f"{hour:02d}")
            Config.update_env_value("SCHEDULE_MINUTE", f"{minute:02d}")

        # 2. Update upcoming calendar items
        res = update_account_default_time(formatted_time, account=account, apply_to_upcoming=apply_to_calendar)

        return jsonify({
            "status": "ok",
            "account": account,
            "new_time": formatted_time,
            "hour": hour,
            "minute": minute,
            "updated_upcoming_count": res.get("updated_upcoming_count", 0),
            "message": f"Jam tayang harian {account.replace('_', ' ').title()} berhasil diubah ke {formatted_time} WIB!"
        })
    except Exception as e:
        logger.error(f"Error updating schedule time for {account}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/settings/credentials", methods=["POST"])
def api_update_credentials():
    """Updates Instagram ID and Access Token for an account."""
    data = request.json or {}
    account = data.get("account", "phono_print")
    acc_id = data.get("instagram_account_id", "").strip()
    token = data.get("instagram_access_token", "").strip()

    if account == "cultivare":
        if acc_id:
            Config.update_env_value("CULTIVARE_INSTAGRAM_ACCOUNT_ID", acc_id)
        if token:
            Config.update_env_value("CULTIVARE_INSTAGRAM_ACCESS_TOKEN", token)
    else:
        if acc_id:
            Config.update_env_value("INSTAGRAM_ACCOUNT_ID", acc_id)
        if token:
            Config.update_env_value("INSTAGRAM_ACCESS_TOKEN", token)

    return jsonify({
        "status": "ok",
        "account": account,
        "message": f"Kredensial {account.replace('_', ' ').title()} berhasil diperbarui!"
    })


@app.route("/api/settings/test-meta", methods=["POST"])
def api_test_meta_token():
    """Validates Instagram Account ID and Access Token via Meta Graph API."""
    import urllib.request
    import urllib.error

    data = request.json or {}
    account = data.get("account", "phono_print")
    cfg = Config.get_account_config(account)
    acc_id = data.get("instagram_account_id") or cfg.get("instagram_account_id")
    token = data.get("instagram_access_token") or cfg.get("instagram_access_token")

    if not acc_id or not token:
        return jsonify({
            "status": "error",
            "message": "Account ID dan Access Token wajib diisi untuk pengetesan."
        }), 400

    try:
        url = f"https://graph.facebook.com/{Config.GRAPH_API_VERSION}/{acc_id}?fields=id,username,name,followers_count,media_count&access_token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta_data = json.loads(resp.read().decode("utf-8"))
            return jsonify({
                "status": "ok",
                "account": account,
                "meta": meta_data,
                "message": f"Koneksi Meta Graph API Berhasil! Terhubung ke Instagram @{meta_data.get('username', acc_id)}."
            })
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body).get("error", {})
            err_msg = err_json.get("message", err_body)
            err_code = err_json.get("code")
            if err_code == 190 or "expired" in err_msg.lower():
                return jsonify({
                    "status": "error",
                    "error_type": "token_expired",
                    "message": "Token Akses Meta telah KEDALUWARSA (Expired)! Dapatkan Page Access Token baru dari Meta Graph API Explorer."
                }), 400
            return jsonify({"status": "error", "message": f"Meta API Error ({err_code}): {err_msg}"}), 400
        except Exception:
            return jsonify({"status": "error", "message": f"Meta API Error: {err_body}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal menghubungi Meta: {str(e)}"}), 500



@app.route("/api/history")
def api_history():
    """Returns publication audit history for the active account."""
    account = request.args.get("account", "phono_print")
    return jsonify({"status": "ok", "account": account, "history": list(reversed(get_history(account)))})


@app.route("/api/pillars")
def api_pillars():
    """Returns the content pillars and topics for the active account."""
    account = request.args.get("account", "phono_print")
    pillars = CULTIVARE_PILLARS if account == "cultivare" else CONTENT_PILLARS
    return jsonify({"status": "ok", "account": account, "pillars": pillars})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """
    Generates preview content via Gemini and renders the banner locally.
    Supports both Phono Print and Cultivare accounts.
    """
    data = request.json or {}
    account = data.get("account", "phono_print")
    category = data.get("category")
    topic_hint = data.get("topic")
    aspect_ratio = data.get("aspect_ratio", "4:5")

    try:
        if account == "cultivare":
            content_engine = CultivareContentGenerator()
            content_dict = content_engine.generate(category_override=category, topic_hint=topic_hint)
            content_dict["account"] = "cultivare"
            headline_display = content_dict.get("headline_en", "")
            subtext_display = f"{content_dict.get('subtext_en', '')} | {content_dict.get('subtext_id', '')}"
        else:
            content_engine = ContentGenerator()
            gen_obj = content_engine.generate(category_override=category, topic_hint=topic_hint)
            content_dict = gen_obj.to_dict()
            content_dict["account"] = "phono_print"
            headline_display = content_dict.get("visual_headline", "")
            subtext_display = content_dict.get("visual_subtext", "")

        image_engine = ImageGenerator()
        local_image_path = image_engine.render(content_dict, aspect_ratio=aspect_ratio)
        filename = Path(local_image_path).name

        return jsonify({
            "status": "ok",
            "account": account,
            "content": content_dict,
            "headline_display": headline_display,
            "subtext_display": subtext_display,
            "aspect_ratio": aspect_ratio,
            "image_filename": filename,
            "image_url": f"/storage/output/{filename}"
        })
    except Exception as e:
        logger.error(f"Error generating preview for {account}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/publish-now", methods=["POST"])
def api_publish_now():
    """
    Executes full pipeline for the specified account:
    Content -> Render -> Cloudinary Upload -> Instagram Post.
    """
    data = request.json or {}
    account = data.get("account", "phono_print")
    cfg = Config.get_account_config(account)
    category = data.get("category")
    topic_hint = data.get("topic")
    aspect_ratio = data.get("aspect_ratio", cfg.get("default_ratio", "4:5"))
    plan_id = data.get("plan_id")

    pre_content = data.get("content")
    pre_image_filename = data.get("image_filename")

    # Validate that account credentials exist
    acc_id = cfg.get("instagram_account_id")
    acc_token = cfg.get("instagram_access_token")
    if not acc_id or not acc_token:
        if account == "cultivare":
            return jsonify({
                "status": "error",
                "message": "Akun Instagram @cultivaree_ belum terhubung ke Meta! Silakan tautkan akun Instagram @cultivaree_ ke Halaman Facebook 'Cultivare.Idea' terlebih dahulu melalui Edit Profil di aplikasi Instagram."
            }), 400
        else:
            return jsonify({
                "status": "error",
                "message": "Instagram Account ID atau Token belum dikonfigurasi di file .env."
            }), 400

    try:
        start_time = time.time()

        # Step 1: Content
        if pre_content and pre_content.get("caption"):
            content_dict = pre_content
            caption = pre_content.get("caption")
            visual_headline = pre_content.get("headline_en") or pre_content.get("visual_headline")
            visual_subtext = pre_content.get("subtext_en") or pre_content.get("visual_subtext")
            cat_name = pre_content.get("category", category)
        else:
            if account == "cultivare":
                content_engine = CultivareContentGenerator()
                content_dict = content_engine.generate(category_override=category, topic_hint=topic_hint)
                content_dict["account"] = "cultivare"
                caption = content_dict.get("caption")
                visual_headline = content_dict.get("headline_en")
                visual_subtext = content_dict.get("subtext_en")
                cat_name = content_dict.get("category")
            else:
                content_engine = ContentGenerator()
                gen_content = content_engine.generate(category_override=category, topic_hint=topic_hint)
                content_dict = gen_content.to_dict()
                content_dict["account"] = "phono_print"
                caption = gen_content.caption
                visual_headline = gen_content.visual_headline
                visual_subtext = gen_content.visual_subtext
                cat_name = gen_content.category

        # Step 2: Image
        if pre_image_filename and (OUTPUT_DIR / pre_image_filename).exists():
            local_image_path = str(OUTPUT_DIR / pre_image_filename)
        else:
            image_engine = ImageGenerator()
            local_image_path = image_engine.render(content_dict, aspect_ratio=aspect_ratio)

        # Step 3: Cloudinary Upload
        storage_engine = CloudStorageUploader()
        public_image_url = storage_engine.upload_image(local_image_path)

        # Step 4: Instagram Publish using account-specific token and ID
        ig_publisher = InstagramPublisher(
            account_id=cfg.get("instagram_account_id"),
            access_token=cfg.get("instagram_access_token")
        )
        publish_result = ig_publisher.publish_feed_post(
            image_url=public_image_url,
            caption=caption
        )

        elapsed = round(time.time() - start_time, 2)
        permalink = publish_result.get("permalink")
        media_id = publish_result.get("media_id")

        # Step 5: Save Audit
        record = {
            "timestamp": datetime.now().isoformat(),
            "account": account,
            "category": cat_name,
            "visual_headline": visual_headline,
            "visual_subtext": visual_subtext,
            "image_url": public_image_url,
            "media_id": media_id,
            "permalink": permalink,
            "elapsed_seconds": elapsed
        }

        save_history(record, account)

        # Update calendar if plan_id exists
        if plan_id:
            update_schedule_status(plan_id, "published", permalink=permalink, account=account)

        return jsonify({
            "status": "ok",
            "account": account,
            "message": f"Berhasil dipublikasikan ke Instagram Feed ({cfg['handle']})!",
            "permalink": permalink,
            "media_id": media_id,
            "image_url": public_image_url,
            "elapsed_seconds": elapsed,
            "content": content_dict
        })

    except Exception as e:
        err_str = str(e)
        logger.error(f"Error publishing post for {account}: {err_str}")
        if "190" in err_str or "expired" in err_str.lower() or "OAuthException" in err_str:
            user_msg = (
                "Token Akses Meta telah KEDALUWARSA (Expired)! "
                "Silakan buka menu '🔑 Kredensial' dan perbarui Access Token dengan Page Access Token yang baru dari Meta Graph API Explorer."
            )
        else:
            user_msg = f"Gagal Publikasi: {err_str}"
        return jsonify({"status": "error", "message": user_msg, "raw_error": err_str}), 500


@app.route("/storage/output/<path:filename>")
@app.route("/output/<path:filename>")
def serve_output_file(filename):
    """Serves generated JPEG banners."""
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/assets/<path:filename>")
def serve_asset_file(filename):
    """Serves brand logos and mockups."""
    return send_from_directory(str(ASSETS_DIR), filename)


def run_admin_server(host="127.0.0.1", port=5000, debug=False):
    """Starts the Flask server."""
    print("=" * 70)
    print(f"PHONO PRINT & CULTIVARE ADMIN DASHBOARD: http://{host}:{port}")
    print("=" * 70)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    run_admin_server(port=port)
