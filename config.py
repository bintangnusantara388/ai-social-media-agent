"""
Central configuration module for the AI Social Media Agent.
Loads settings from .env file and provides typed access and validation.
"""

import os
from pathlib import Path
# Base directory paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR = BASE_DIR / "storage"
OUTPUT_DIR = STORAGE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # Manual lightweight fallback parser for .env if python-dotenv is not installed
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v




class Config:
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Branding (Default: Phono Print Tegal - Creative)
    BRAND_NAME: str = os.getenv("BRAND_NAME", "PHONO PRINT")
    BRAND_TAGLINE: str = os.getenv("BRAND_TAGLINE", "TEGAL - CREATIVE PRINT LAB")
    BRAND_HANDLE: str = os.getenv("BRAND_HANDLE", "@phonoprint.tegal")
    POST_ASPECT_RATIO: str = os.getenv("POST_ASPECT_RATIO", "4:5")


    # Cloud Storage Settings
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "cloudinary").lower()
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    # AWS S3 Settings (Alternative)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")

    # Meta Instagram Graph API
    GRAPH_API_VERSION: str = os.getenv("GRAPH_API_VERSION", "v19.0")
    INSTAGRAM_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    # Cultivare Meta Credentials (Optional override, defaults to primary if sharing app)
    CULTIVARE_INSTAGRAM_ACCOUNT_ID: str = os.getenv("CULTIVARE_INSTAGRAM_ACCOUNT_ID", "")
    CULTIVARE_INSTAGRAM_ACCESS_TOKEN: str = os.getenv("CULTIVARE_INSTAGRAM_ACCESS_TOKEN", "")

    # Multi-Account Configurations
    @classmethod
    def get_account_config(cls, account_id: str = "phono_print") -> dict:
        acc_id = "cultivare" if account_id == "cultivare" else "phono_print"
        if acc_id == "cultivare":
            return {
                "id": "cultivare",
                "name": os.getenv("CULTIVARE_BRAND_NAME", "Cultivare Collective"),
                "handle": os.getenv("CULTIVARE_BRAND_HANDLE", "@cultivaree_"),
                "tagline": os.getenv("CULTIVARE_BRAND_TAGLINE", "Strategic Brand Development & Global Economy Culture"),
                "logo_file": "cultivare_logo.png",
                "theme": "forest_green_editorial",
                "schedule_hour": int(os.getenv("CULTIVARE_SCHEDULE_HOUR", "18")),
                "schedule_minute": int(os.getenv("CULTIVARE_SCHEDULE_MINUTE", "0")),
                "default_ratio": "4:5",
                "instagram_account_id": cls.CULTIVARE_INSTAGRAM_ACCOUNT_ID,
                "instagram_access_token": cls.CULTIVARE_INSTAGRAM_ACCESS_TOKEN,
                "niche": "Global Economy, Business Culture & Strategic Brand Growth"
            }
        return {
            "id": "phono_print",
            "name": cls.BRAND_NAME,
            "handle": cls.BRAND_HANDLE,
            "tagline": cls.BRAND_TAGLINE,
            "logo_file": "phono_print_logo_clean.png",
            "theme": "dark_tech_print",
            "schedule_hour": cls.SCHEDULE_HOUR,
            "schedule_minute": cls.SCHEDULE_MINUTE,
            "default_ratio": cls.POST_ASPECT_RATIO,
            "instagram_account_id": cls.INSTAGRAM_ACCOUNT_ID,
            "instagram_access_token": cls.INSTAGRAM_ACCESS_TOKEN,
            "niche": "Percetakan Industri & Undangan Digital"
        }

    # Scheduler Settings
    SCHEDULE_HOUR: int = int(os.getenv("SCHEDULE_HOUR", "9"))
    SCHEDULE_MINUTE: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jakarta")

    @classmethod
    def update_env_value(cls, key: str, value: str):
        """Updates a key-value in .env file and syncs os.environ and Config class in memory."""
        env_path = BASE_DIR / ".env"
        lines = []
        found = False
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"{key}={value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        os.environ[key] = str(value)

        # In-memory attribute sync
        if key == "SCHEDULE_HOUR":
            cls.SCHEDULE_HOUR = int(value)
        elif key == "SCHEDULE_MINUTE":
            cls.SCHEDULE_MINUTE = int(value)
        elif key == "CULTIVARE_INSTAGRAM_ACCOUNT_ID":
            cls.CULTIVARE_INSTAGRAM_ACCOUNT_ID = str(value)
        elif key == "CULTIVARE_INSTAGRAM_ACCESS_TOKEN":
            cls.CULTIVARE_INSTAGRAM_ACCESS_TOKEN = str(value)
        elif key == "INSTAGRAM_ACCOUNT_ID":
            cls.INSTAGRAM_ACCOUNT_ID = str(value)
        elif key == "INSTAGRAM_ACCESS_TOKEN":
            cls.INSTAGRAM_ACCESS_TOKEN = str(value)

    @classmethod
    def validate_for_execution(cls, dry_run: bool = False):
        """Validate required credentials according to execution mode."""
        errors = []

        # Validate LLM
        if not dry_run:
            if cls.LLM_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
                errors.append("GEMINI_API_KEY must be set when LLM_PROVIDER is 'gemini'")
            elif cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY must be set when LLM_PROVIDER is 'openai'")


        # If not dry run, validate storage and Meta API
        if not dry_run:
            if cls.STORAGE_PROVIDER == "cloudinary":
                if not (cls.CLOUDINARY_CLOUD_NAME and cls.CLOUDINARY_API_KEY and cls.CLOUDINARY_API_SECRET):
                    errors.append("Cloudinary credentials (CLOUD_NAME, API_KEY, API_SECRET) are required.")
            elif cls.STORAGE_PROVIDER == "s3":
                if not (cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY and cls.AWS_BUCKET_NAME):
                    errors.append("AWS S3 credentials (KEY_ID, SECRET_KEY, BUCKET_NAME) are required.")

            if not cls.INSTAGRAM_ACCOUNT_ID:
                errors.append("INSTAGRAM_ACCOUNT_ID is required for publishing.")
            if not cls.INSTAGRAM_ACCESS_TOKEN:
                errors.append("INSTAGRAM_ACCESS_TOKEN is required for publishing.")

        if errors:
            raise ValueError("Configuration Validation Failed:\n- " + "\n- ".join(errors))
