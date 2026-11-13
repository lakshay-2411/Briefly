import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, pipeline
from app.config import settings
from app.routes import briefings, episodes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()
    yield
    pipeline.executor.shutdown(wait=False, cancel_futures=True)
    db.pool.close()


app = FastAPI(title="Daily Research Podcast API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(briefings.router)
app.include_router(episodes.router)


@app.get("/health")
def health():
    # Hit every 5 min by the keep-alive pinger, so it must stay cheap (no DB).
    return {"status": "ok"}
