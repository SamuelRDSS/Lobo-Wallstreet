from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import FRONT_DIR, IS_VERCEL, OUTPUT_DIR, ensure_directories
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

if IS_VERCEL:
    @app.get("/saida/{file_path:path}", include_in_schema=False)
    def generated_file(file_path: str) -> FileResponse:
        output_dir = OUTPUT_DIR.resolve()
        path = (output_dir / file_path).resolve()
        try:
            path.relative_to(output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        return FileResponse(path)
else:
    app.mount("/saida", StaticFiles(directory=OUTPUT_DIR), name="saida")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/front/")
