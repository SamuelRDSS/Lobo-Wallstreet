from __future__ import annotations

from backend.app.config import DEFAULT_INPUT_CSV, N8N_WEBHOOK_URL, OUTPUT_DIR


class N8nService:
    def __init__(self, webhook_url: str = N8N_WEBHOOK_URL) -> None:
        self.webhook_url = webhook_url

    def analyze(self, csv_path: str | None = None, output_dir: str | None = None, enrich_web: bool = True) -> dict:
        payload = {
            "csvPath": csv_path or str(DEFAULT_INPUT_CSV),
            "outputDir": output_dir or str(OUTPUT_DIR),
            "enrichWeb": enrich_web,
        }
        import httpx

        with httpx.Client(timeout=300) as client:
            response = client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
