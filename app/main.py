import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.config import settings
from app.database import async_engine
from app.observability.logging_config import setup_logging

setup_logging()

from app.chat import router as chat  # noqa: E402 must import after setup_logging()
from app.routers import auth, requests, templates  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await async_engine.dispose()


logger = logging.getLogger(__name__)

app = FastAPI(title="pdfer", debug=settings.DEBUG, lifespan=lifespan)


@app.middleware("http")
async def measure_time(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000

    EXCLUDED_PATHS = {"/metrics", "/health"}

    if request.url.path not in EXCLUDED_PATHS:
        logger.info(
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.2f}ms"
        )

    return response


app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(requests.router)
app.include_router(chat.router)


# Instrumented after routes are registered so the instrumentator can see the route templates.
from app.observability.metrics import init_metrics  # noqa: E402

init_metrics(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
