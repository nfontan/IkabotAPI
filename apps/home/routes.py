import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from apps.models import HealthResponse

router = APIRouter()

start_time = time.time()


@router.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse("<h1>Ikabot API</h1><p>API is running. See <a href='/docs'>/docs</a> for documentation.</p>")


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy", version="2.0.0", uptime=time.time() - start_time
    )
