"""
Cloud Storage Module
Uploads local images to public cloud storage (Cloudinary or AWS S3)
and returns a public, secure HTTPS URL required by the Instagram Graph API.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)


class CloudStorageUploader:
    """Handles image uploads to Cloudinary or AWS S3."""

    def __init__(self):
        self.provider = Config.STORAGE_PROVIDER
        logger.info(f"Initialized CloudStorageUploader with provider: {self.provider}")

    def upload_image(self, file_path: str, public_id: Optional[str] = None) -> str:
        """
        Uploads a local image file to cloud storage.
        Returns the public HTTPS URL.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file does not exist: {file_path}")

        logger.info(f"Uploading {file_path} via provider '{self.provider}'...")

        if self.provider == "cloudinary":
            return self._upload_to_cloudinary(path, public_id)
        elif self.provider == "s3":
            return self._upload_to_s3(path, public_id)
        elif self.provider == "mock" or self.provider == "local_test":
            logger.warning("Using mock storage provider. URL will not work on production Instagram API.")
            return f"https://images.unsplash.com/photo-1562654501-a0ccc0fc3fb1?q=80&w=1080&auto=format&fit=crop"
        else:
            raise ValueError(f"Unsupported storage provider: {self.provider}")

    def _upload_to_cloudinary(self, path: Path, public_id: Optional[str]) -> str:
        """Upload image to Cloudinary and retrieve direct secure_url."""
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError:
            raise ImportError(
                "Cloudinary SDK is not installed. Run: pip install cloudinary"
            )

        if not (Config.CLOUDINARY_CLOUD_NAME and Config.CLOUDINARY_API_KEY and Config.CLOUDINARY_API_SECRET):
            raise ValueError("Cloudinary credentials are incomplete in .env.")

        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET,
            secure=True
        )

        folder = "print_social_agent"
        upload_params = {
            "folder": folder,
            "resource_type": "image",
            "overwrite": True
        }
        if public_id:
            upload_params["public_id"] = public_id

        try:
            response = cloudinary.uploader.upload(str(path), **upload_params)
            secure_url = response.get("secure_url")
            if not secure_url:
                raise RuntimeError(f"Cloudinary upload succeeded but secure_url missing: {response}")
            logger.info(f"Cloudinary upload successful! Public URL: {secure_url}")
            return secure_url
        except Exception as e:
            logger.error(f"Failed to upload to Cloudinary: {e}")
            raise

    def _upload_to_s3(self, path: Path, object_key: Optional[str]) -> str:
        """Upload image to AWS S3 and construct public HTTPS URL."""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("boto3 is not installed. Run: pip install boto3")

        if not (Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY and Config.AWS_BUCKET_NAME):
            raise ValueError("AWS S3 credentials are incomplete in .env.")

        s3 = boto3.client(
            "s3",
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )

        key = object_key or f"posts/{path.name}"
        extra_args = {"ContentType": "image/jpeg"}

        try:
            s3.upload_file(str(path), Config.AWS_BUCKET_NAME, key, ExtraArgs=extra_args)
            public_url = f"https://{Config.AWS_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{key}"
            logger.info(f"S3 upload successful! Public URL: {public_url}")
            return public_url
        except ClientError as e:
            logger.error(f"Failed to upload to AWS S3: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uploader = CloudStorageUploader()
    print(f"CloudStorageUploader ready for provider: {uploader.provider}")
