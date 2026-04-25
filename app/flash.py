"""Cookie-based flash messages for server-side rendered pages."""
import json
from typing import Optional, Tuple

from fastapi import Request, Response

FLASH_COOKIE = "_flash"


def set_flash(response: Response, message: str, category: str = "success"):
    """Set a flash message to be shown on the next page load.

    Categories: success, error, info, warning
    """
    data = json.dumps({"msg": message, "cat": category})
    response.set_cookie(
        FLASH_COOKIE,
        data,
        httponly=True,
        samesite="lax",
        max_age=30,
    )


def get_flash(request: Request) -> Optional[Tuple[str, str]]:
    """Read and consume the flash message. Returns (message, category) or None."""
    raw = request.cookies.get(FLASH_COOKIE)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("msg", ""), data.get("cat", "info")
    except (json.JSONDecodeError, AttributeError):
        return None


def clear_flash(response: Response):
    """Remove the flash cookie."""
    response.delete_cookie(FLASH_COOKIE)
