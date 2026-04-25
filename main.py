from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import config
from app.database import Base, engine
from app.flash import get_flash, FLASH_COOKIE
from app.routers import auth_routes, student_routes, professor_routes, api_routes

# Ensure templating module is imported (registers filters/globals)
import app.templating  # noqa: F401

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=config.SITE_NAME, debug=config.DEBUG)


class FlashMiddleware(BaseHTTPMiddleware):
    """Read flash cookie on request, clear it on response."""

    async def dispatch(self, request: Request, call_next):
        request.state.flash = get_flash(request)
        response = await call_next(request)
        # Clear flash cookie after reading it
        if request.state.flash:
            response.delete_cookie(FLASH_COOKIE)
        return response


app.add_middleware(FlashMiddleware)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(professor_routes.router)
app.include_router(api_routes.router)


@app.get("/")
def root():
    return RedirectResponse("/dashboard", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
