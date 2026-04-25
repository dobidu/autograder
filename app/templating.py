"""Shared Jinja2 templates instance for all routers."""
import json
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import markdown as md

import config

templates = Jinja2Templates(directory="templates")
templates.env.globals["site_name"] = config.SITE_NAME
templates.env.auto_reload = True


def render_markdown(text: str) -> str:
    return md.markdown(text, extensions=["fenced_code", "tables", "codehilite"])


def time_remaining(deadline) -> str:
    """Return human-readable time remaining until deadline, or 'Encerrado'."""
    now = datetime.now(timezone.utc)
    dl = deadline
    if dl.tzinfo is None:
        dl = dl.replace(tzinfo=timezone.utc)
    diff = dl - now
    if diff.total_seconds() <= 0:
        return "Encerrado"
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    if days > 7:
        return "Faltam {} dias".format(days)
    elif days > 0:
        return "Faltam {}d {}h".format(days, hours)
    elif hours > 0:
        return "Faltam {}h {}min".format(hours, minutes)
    else:
        return "Faltam {}min".format(max(1, minutes))


templates.env.filters["markdown"] = render_markdown
templates.env.filters["from_json"] = lambda s: json.loads(s) if s else []
templates.env.filters["time_remaining"] = time_remaining


def render(name: str, request: Request, context: Dict[str, Any] = None, status_code: int = 200) -> HTMLResponse:
    """Render a template with automatic flash message and path injection."""
    ctx = {"request": request}
    # Inject flash message from middleware
    flash = getattr(request.state, "flash", None)
    if flash:
        ctx["flash_message"] = flash[0]
        ctx["flash_category"] = flash[1]
    # Inject current path for nav highlighting
    ctx["current_path"] = request.url.path
    if context:
        ctx.update(context)
    return templates.TemplateResponse(name, ctx, status_code=status_code)
