"""
Multi-Account Content Calendar & Schedule Management Module
Supports:
- phono_print (Phono Print Tegal - Percetakan & Undangan Digital)
- cultivare (Cultivare Collective - Global Economy, Business Culture & Strategic Branding)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import STORAGE_DIR
from content_generator import CONTENT_PILLARS
from cultivare_content import CULTIVARE_PILLARS

logger = logging.getLogger(__name__)


def get_calendar_file(account: str = "phono_print") -> Path:
    """Returns the JSON path for the specified account."""
    if account == "cultivare":
        return STORAGE_DIR / "content_plan_cultivare.json"
    return STORAGE_DIR / "content_plan.json"


def get_default_30_day_plan(account: str = "phono_print") -> List[Dict[str, Any]]:
    """Generates a balanced 30-day content calendar cycling through all pillars for the account."""
    today = datetime.now()
    plan = []

    if account == "cultivare":
        pillars = CULTIVARE_PILLARS
        default_time = "18:00"
        default_ratio = "4:5"
    else:
        pillars = CONTENT_PILLARS
        default_time = "09:00"
        default_ratio = "4:5"

    total_pillars = len(pillars)
    topic_pointers = {p["category"]: 0 for p in pillars}

    for day_offset in range(30):
        scheduled_date = today + timedelta(days=day_offset)
        date_str = scheduled_date.strftime("%Y-%m-%d")

        pillar = pillars[day_offset % total_pillars]
        category = pillar["category"]

        topics = pillar["topics"]
        topic_ptr = topic_pointers[category] % len(topics)
        topic = topics[topic_ptr]
        topic_pointers[category] += 1

        if account == "cultivare":
            ratio = "4:5"
        else:
            ratio = "4:5" if "undangan" in category.lower() or "promo" in category.lower() else ("4:5" if day_offset % 3 != 0 else "1:1")

        plan.append({
            "id": f"{account}_{scheduled_date.strftime('%Y%m%d')}",
            "account": account,
            "date": date_str,
            "time": default_time,
            "category": category,
            "topic": topic,
            "aspect_ratio": ratio,
            "status": "scheduled" if day_offset > 0 else ("published" if account == "phono_print" else "scheduled"),
            "permalink": "https://www.instagram.com/p/DfGqP2TGFq1/" if (day_offset == 0 and account == "phono_print") else None,
            "notes": f"Auto-generated 30-day cycle for {account}"
        })

    return plan


def load_content_plan(account: str = "phono_print") -> List[Dict[str, Any]]:
    """Loads the content plan from JSON, or initializes with default 30-day plan."""
    cal_file = get_calendar_file(account)
    if not cal_file.exists():
        default_plan = get_default_30_day_plan(account)
        save_content_plan(default_plan, account)
        return default_plan

    try:
        with open(cal_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading content plan for {account}: {e}")
        return get_default_30_day_plan(account)


def save_content_plan(plan: List[Dict[str, Any]], account: str = "phono_print") -> bool:
    """Saves the content plan to JSON file."""
    cal_file = get_calendar_file(account)
    try:
        cal_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cal_file, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving content plan for {account}: {e}")
        return False


def add_schedule_item(date: str, time: str, category: str, topic: str, aspect_ratio: str = "4:5", notes: str = "", account: str = "phono_print") -> Dict[str, Any]:
    """Adds a new schedule item to the content calendar."""
    plan = load_content_plan(account)
    new_item = {
        "id": f"{account}_{date.replace('-', '')}_{int(datetime.now().timestamp())}",
        "account": account,
        "date": date,
        "time": time or ("18:00" if account == "cultivare" else "09:00"),
        "category": category,
        "topic": topic,
        "aspect_ratio": aspect_ratio,
        "status": "scheduled",
        "permalink": None,
        "notes": notes
    }
    plan.append(new_item)
    plan.sort(key=lambda x: f"{x['date']} {x.get('time', '00:00')}")
    save_content_plan(plan, account)
    return new_item


def update_schedule_status(item_id: str, status: str, permalink: Optional[str] = None, account: str = "phono_print") -> bool:
    """Updates the status and optional permalink of a schedule item."""
    plan = load_content_plan(account)
    updated = False
    for item in plan:
        if item["id"] == item_id:
            item["status"] = status
            if permalink:
                item["permalink"] = permalink
            updated = True
            break
    if updated:
        save_content_plan(plan, account)
    return updated


def delete_schedule_item(item_id: str, account: str = "phono_print") -> bool:
    """Deletes an item from the content plan."""
    plan = load_content_plan(account)
    filtered = [p for p in plan if p["id"] != item_id]
    if len(filtered) != len(plan):
        save_content_plan(filtered, account)
        return True
    return False


def edit_schedule_item(item_id: str, date: str, time: str, category: str, topic: str, aspect_ratio: str = "4:5", notes: str = "", account: str = "phono_print") -> Optional[Dict[str, Any]]:
    """Updates fields of an existing schedule item in the content calendar."""
    plan = load_content_plan(account)
    updated_item = None
    for item in plan:
        if item["id"] == item_id:
            item["date"] = date
            item["time"] = time
            item["category"] = category
            item["topic"] = topic
            item["aspect_ratio"] = aspect_ratio
            if notes is not None:
                item["notes"] = notes
            updated_item = item
            break
    if updated_item:
        plan.sort(key=lambda x: f"{x['date']} {x.get('time', '00:00')}")
        save_content_plan(plan, account)
    return updated_item


def update_account_default_time(new_time: str, account: str = "phono_print", apply_to_upcoming: bool = True) -> Dict[str, Any]:
    """
    Updates the global schedule time for an account.
    new_time is in 'HH:MM' format (e.g. '09:30' or '19:00').
    If apply_to_upcoming is True, all calendar items with status == 'scheduled' are updated to new_time.
    """
    parts = new_time.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    formatted_time = f"{hour:02d}:{minute:02d}"

    updated_count = 0
    if apply_to_upcoming:
        plan = load_content_plan(account)
        for item in plan:
            if item.get("status") == "scheduled":
                item["time"] = formatted_time
                updated_count += 1
        save_content_plan(plan, account)

    return {
        "account": account,
        "new_time": formatted_time,
        "hour": hour,
        "minute": minute,
        "updated_upcoming_count": updated_count
    }

