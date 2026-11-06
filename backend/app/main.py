from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import FRONT_DIR, OUTPUT_DIR, ensure_directories
from backend.app.routes.api import router as api_router


ensure_directories()

app = FastAPI(title="Lobo Walstreet", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8088", "http://127.0.0.1:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/front", StaticFiles(directory=FRONT_DIR, html=True), name="front")
app.mount("/saida", StaticFiles(directory=OUTPUT_DIR), name="saida")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/front/")
