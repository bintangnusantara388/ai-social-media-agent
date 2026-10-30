"""
Instagram Graph API Publisher Module
Publishes images to Instagram Business/Creator feed using the official 2-step Meta Graph API:
Step 1: Create Media Container (POST /{ig_user_id}/media)
Step 2: Check Container Status & Wait for FINISHED (GET /{creation_id})
Step 3: Publish Container (POST /{ig_user_id}/media_publish)
"""

import time
import logging
from typing import Dict, Any, Optional
import requests

from config import Config

logger = logging.getLogger(__name__)


class InstagramAPIError(Exception):
    """Custom exception for Meta Graph API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_data = error_data or {}


class InstagramPublisher:
    """Official Meta Graph API Publisher for Instagram Feed."""

    def __init__(self, account_id: Optional[str] = None, access_token: Optional[str] = None):
        self.api_version = Config.GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.account_id = account_id or Config.INSTAGRAM_ACCOUNT_ID
        self.access_token = access_token or Config.INSTAGRAM_ACCESS_TOKEN

    def publish_feed_post(self, image_url: str, caption: str, poll_interval: int = 3, max_retries: int = 15) -> Dict[str, Any]:
        """
        Orchestrates full 2-step publish workflow:
        1. Create media container
        2. Poll container status until FINISHED
        3. Publish container
        4. Retrieve live post permalink
        """
        if not self.account_id or not self.access_token:
            raise InstagramAPIError("INSTAGRAM_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN is missing in config.")

        logger.info(f"Starting Instagram publishing pipeline for account ID: {self.account_id}...")

        # Step 1: Create Media Container
        creation_id = self.create_media_container(image_url, caption)
        logger.info(f"Container created successfully. Creation ID: {creation_id}")

        # Step 2: Poll container status
        self.wait_for_container_ready(creation_id, poll_interval=poll_interval, max_retries=max_retries)

        # Step 3: Publish Media Container
        media_id = self.publish_container(creation_id)
        logger.info(f"Media successfully published! Media ID: {media_id}")

        # Step 4: Fetch permalink for verification
        post_details = self.get_post_details(media_id)
        permalink = post_details.get("permalink", f"https://instagram.com/p/{media_id}")
        logger.info(f"Post is live on Instagram: {permalink}")

        return {
            "success": True,
            "media_id": media_id,
            "creation_id": creation_id,
            "permalink": permalink,
            "timestamp": post_details.get("timestamp")
        }

    def create_media_container(self, image_url: str, caption: str) -> str:
        """
        Step 1: Creates an Instagram Media Container.
        POST https://graph.facebook.com/{version}/{ig_user_id}/media
        """
        endpoint = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }

        try:
            resp = requests.post(endpoint, data=payload, timeout=30)
            data = resp.json()

            if resp.status_code != 200 or "id" not in data:
                self._handle_error_response(resp, "Failed to create media container")

            return data["id"]
        except requests.RequestException as e:
            logger.error(f"Network error creating media container: {e}")
            raise InstagramAPIError(f"HTTP request failed: {e}")

    def wait_for_container_ready(self, creation_id: str, poll_interval: int = 3, max_retries: int = 15) -> bool:
        """
        Step 2: Checks the status of the container until status_code == 'FINISHED'.
        GET https://graph.facebook.com/{version}/{creation_id}?fields=status_code,status
        """
        endpoint = f"{self.base_url}/{creation_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }

        for attempt in range(1, max_retries + 1):
            logger.info(f"Polling container status (Attempt {attempt}/{max_retries})...")
            try:
                resp = requests.get(endpoint, params=params, timeout=20)
                data = resp.json()

                if resp.status_code != 200:
                    self._handle_error_response(resp, f"Failed to check status for container {creation_id}")

                status_code = data.get("status_code")
                logger.info(f"Container {creation_id} current status: {status_code}")

                if status_code == "FINISHED":
                    return True
                elif status_code == "IN_PROGRESS":
                    time.sleep(poll_interval)
                elif status_code == "ERROR":
                    error_message = data.get("status", "Unknown container processing error")
                    raise InstagramAPIError(f"Container processing resulted in ERROR: {error_message}", error_data=data)
                elif status_code == "EXPIRED":
                    raise InstagramAPIError(f"Container {creation_id} has EXPIRED.", error_data=data)
                else:
                    # Some endpoints return status directly as 'FINISHED' or empty
                    time.sleep(poll_interval)
            except requests.RequestException as e:
                logger.warning(f"Polling request error (Attempt {attempt}): {e}")
                time.sleep(poll_interval)

        raise InstagramAPIError(f"Container {creation_id} timed out before reaching FINISHED status.")

    def publish_container(self, creation_id: str) -> str:
        """
        Step 3: Publishes the validated container to the user's feed.
        POST https://graph.facebook.com/{version}/{ig_user_id}/media_publish
        """
        endpoint = f"{self.base_url}/{self.account_id}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }

        try:
            resp = requests.post(endpoint, data=payload, timeout=30)
            data = resp.json()

            if resp.status_code != 200 or "id" not in data:
                self._handle_error_response(resp, "Failed to publish media container")

            return data["id"]
        except requests.RequestException as e:
            logger.error(f"Network error during media publishing: {e}")
            raise InstagramAPIError(f"Publish HTTP request failed: {e}")

    def get_post_details(self, media_id: str) -> Dict[str, Any]:
        """
        Retrieves post metadata such as permalink and timestamp.
        GET https://graph.facebook.com/{version}/{media_id}?fields=id,permalink,timestamp
        """
        endpoint = f"{self.base_url}/{media_id}"
        params = {
            "fields": "id,permalink,timestamp,media_type",
            "access_token": self.access_token
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            logger.warning(f"Could not fetch post details for {media_id}: {e}")
            return {}

    def _handle_error_response(self, response: requests.Response, context: str):
        """Extracts descriptive error message from Meta Graph API response."""
        try:
            err_data = response.json()
            err_obj = err_data.get("error", {})
            message = err_obj.get("message", "No message provided")
            code = err_obj.get("code")
            subcode = err_obj.get("error_subcode")
            fbtrace_id = err_obj.get("fbtrace_id")
            err_type = err_obj.get("type", "OAuthException")

            detailed_msg = (
                f"{context} [HTTP {response.status_code}]: {message} "
                f"(Type: {err_type}, Code: {code}, Subcode: {subcode}, fbtrace: {fbtrace_id})"
            )
            logger.error(detailed_msg)
            raise InstagramAPIError(detailed_msg, status_code=response.status_code, error_data=err_data)
        except (ValueError, KeyError):
            raw_text = response.text
            msg = f"{context} [HTTP {response.status_code}]: {raw_text}"
            logger.error(msg)
            raise InstagramAPIError(msg, status_code=response.status_code)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    publisher = InstagramPublisher()
    print("InstagramPublisher initialized.")
