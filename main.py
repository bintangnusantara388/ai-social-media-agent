"""
Main Orchestration & Task Scheduler Module
Coordinates the entire end-to-end pipeline:
LLM Content Engine -> Image Renderer (1080x1080) -> Cloud Storage Upload -> Instagram Graph API Publish
"""

import sys
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config, STORAGE_DIR
from content_generator import ContentGenerator, GeneratedContent
from cultivare_content import CultivareContentGenerator
from image_generator import ImageGenerator
from cloud_storage import CloudStorageUploader
from instagram_publisher import InstagramPublisher, InstagramAPIError

# Windows UTF-8 console output fix for emojis
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure unified logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(STORAGE_DIR / "agent.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("SocialMediaAgent")

HISTORY_FILE = STORAGE_DIR / "publish_history.json"


def save_to_history(record: Dict[str, Any], account: str = "phono_print"):
    """Appends successful publication records to local audit history."""
    hist_file = STORAGE_DIR / f"publish_history_{account}.json" if account == "cultivare" else STORAGE_DIR / "publish_history.json"
    history = []
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(record)
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def run_daily_publisher(category: Optional[str] = None, dry_run: bool = False, aspect_ratio: Optional[str] = None, account: str = "phono_print") -> Dict[str, Any]:
    """
    Main orchestration function running the end-to-end social media publishing pipeline.
    Supports 'phono_print' and 'cultivare'.
    """
    start_time = time.time()
    cfg = Config.get_account_config(account)
    ratio = aspect_ratio or cfg.get("default_ratio", "4:5")
    logger.info("=" * 70)
    logger.info(f"STARTING SOCIAL MEDIA AGENT RUN [{cfg['name'].upper()}] (Dry Run: {dry_run}, Ratio: {ratio})")
    logger.info("=" * 70)

    # 0. Validate Configuration
    try:
        Config.validate_for_execution(dry_run=dry_run)
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise

    # 1. Content Generation Engine
    logger.info(f">>> STEP 1: Generating Content for {cfg['name']} via LLM...")
    if account == "cultivare":
        content_engine = CultivareContentGenerator()
        content_dict = content_engine.generate(category_override=category)
        content_dict["account"] = "cultivare"
        caption = content_dict.get("caption")
        visual_headline = content_dict.get("headline_en")
        visual_subtext = content_dict.get("subtext_en")
        cat_name = content_dict.get("category")
    else:
        content_engine = ContentGenerator()
        content_obj: GeneratedContent = content_engine.generate(category_override=category)
        content_dict = content_obj.to_dict()
        content_dict["account"] = "phono_print"
        caption = content_obj.caption
        visual_headline = content_obj.visual_headline
        visual_subtext = content_obj.visual_subtext
        cat_name = content_obj.category

    logger.info(f"Generated Category : {cat_name}")
    logger.info(f"Visual Headline    : {visual_headline}")
    logger.info(f"Visual Subtext     : {visual_subtext}")
    logger.info(f"Caption Length     : {len(caption)} characters")

    # 2. Image Rendering Engine
    logger.info(f">>> STEP 2: Rendering High-Resolution Banner Image ({ratio})...")
    image_engine = ImageGenerator()
    image_path = image_engine.render(content_dict, aspect_ratio=ratio)
    logger.info(f"Local Image Rendered at: {image_path}")

    # If Dry Run mode, stop here and display generated outputs
    if dry_run:
        logger.info(">>> [DRY RUN ACTIVE] Skipping Cloud Storage Upload and Instagram Meta API.")
        logger.info("\n" + "="*50 + " GENERATED CAPTION " + "="*50)
        try:
            print(caption)
        except UnicodeEncodeError:
            print(caption.encode("ascii", errors="replace").decode("ascii"))

        logger.info("=" * 119)
        return {
            "status": "dry_run_success",
            "account": account,
            "content": content_dict,
            "local_image_path": image_path,
            "elapsed_seconds": round(time.time() - start_time, 2)
        }

    # 3. Cloud Storage Upload
    logger.info(">>> STEP 3: Uploading Banner Image to Public Cloud Storage...")
    storage_engine = CloudStorageUploader()
    public_image_url = storage_engine.upload_image(image_path)
    logger.info(f"Public Secure Image URL: {public_image_url}")

    # 4. Instagram Graph API Publish
    logger.info(f">>> STEP 4: Publishing to Instagram Feed ({cfg['handle']}) via Meta Graph API...")
    ig_publisher = InstagramPublisher(
        account_id=cfg.get("instagram_account_id"),
        access_token=cfg.get("instagram_access_token")
    )
    publish_result = ig_publisher.publish_feed_post(
        image_url=public_image_url,
        caption=caption
    )

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"SUCCESS! Published to Instagram in {elapsed}s.")
    logger.info(f"Live Permalink: {publish_result.get('permalink')}")

    # 5. Save Record to Audit History
    audit_record = {
        "timestamp": datetime.now().isoformat(),
        "account": account,
        "category": cat_name,
        "visual_headline": visual_headline,
        "visual_subtext": visual_subtext,
        "image_url": public_image_url,
        "media_id": publish_result.get("media_id"),
        "permalink": publish_result.get("permalink"),
        "elapsed_seconds": elapsed
    }
    save_to_history(audit_record, account=account)

    logger.info("=" * 70)
    logger.info(f"AGENT RUN FOR {cfg['name']} COMPLETED SUCCESSFULLY.")
    logger.info("=" * 70)
    return audit_record


def start_scheduler():
    """Starts the APScheduler background daemon to publish daily for both accounts at their configured hours."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler is not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=Config.TIMEZONE)

    # Job 1: Phono Print
    phono_cfg = Config.get_account_config("phono_print")
    p_hour = phono_cfg["schedule_hour"]
    p_minute = phono_cfg["schedule_minute"]
    scheduler.add_job(
        lambda: run_daily_publisher(account="phono_print"),
        trigger=CronTrigger(hour=p_hour, minute=p_minute, timezone=Config.TIMEZONE),
        id="phono_print_daily_publisher",
        name="Phono Print Daily Printing & Wedding Publisher",
        replace_existing=True
    )
    logger.info(f"[+] Registered Job: Phono Print at {p_hour:02d}:{p_minute:02d} ({Config.TIMEZONE})")

    # Job 2: Cultivare Collective
    cultivare_cfg = Config.get_account_config("cultivare")
    c_hour = cultivare_cfg["schedule_hour"]
    c_minute = cultivare_cfg["schedule_minute"]
    scheduler.add_job(
        lambda: run_daily_publisher(account="cultivare"),
        trigger=CronTrigger(hour=c_hour, minute=c_minute, timezone=Config.TIMEZONE),
        id="cultivare_daily_publisher",
        name="Cultivare Collective Daily Business & Economy Publisher",
        replace_existing=True
    )
    logger.info(f"[+] Registered Job: Cultivare Collective at {c_hour:02d}:{c_minute:02d} ({Config.TIMEZONE})")

    print("\n" + "="*70)
    print("AI SOCIAL MEDIA MULTI-ACCOUNT SCHEDULER ACTIVE!")
    print(f"- Phono Print (@phono.print_tegal): Setiap hari jam {p_hour:02d}:{p_minute:02d} {Config.TIMEZONE}")
    print(f"- Cultivare (@cultivaree_):        Setiap hari jam {c_hour:02d}:{c_minute:02d} {Config.TIMEZONE}")
    print("Tekan Ctrl+C untuk menghentikan scheduler.")
    print("="*70 + "\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="Multi-Account AI Social Media Agent")
    parser.add_argument("--now", action="store_true", help="Execute the publishing pipeline immediately once.")
    parser.add_argument("--dry-run", action="store_true", help="Run content generation & image rendering without publishing.")
    parser.add_argument("--schedule", action="store_true", help="Start continuous daily scheduler daemon for both accounts.")
    parser.add_argument("--account", type=str, default="phono_print", choices=["phono_print", "cultivare", "all"], help="Target account (phono_print, cultivare, or all).")
    parser.add_argument("--category", type=str, default=None, help="Filter by specific content category.")
    parser.add_argument("--ratio", type=str, default=None, choices=["4:5", "1:1"], help="Set post aspect ratio (4:5 or 1:1). Defaults to account default.")

    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    elif args.now or args.dry_run:
        targets = ["phono_print", "cultivare"] if args.account == "all" else [args.account]
        for acc in targets:
            run_daily_publisher(
                category=args.category,
                dry_run=args.dry_run,
                aspect_ratio=args.ratio,
                account=acc
            )
    else:
        parser.print_help()




if __name__ == "__main__":
    main()
