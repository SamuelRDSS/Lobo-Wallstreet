from __future__ import annotations

from pathlib import Path

from backend.app.config import CONFIG_DIR, DEFAULT_INPUT_CSV, OUTPUT_DIR
from backend.app.services.n8n_service import N8nService


class AnalyzerService:
    def __init__(self) -> None:
        self.n8n = N8nService()

    def run_via_n8n(self, csv_path: str | None = None, output_dir: str | None = None, enrich_web: bool = True) -> dict:
        return self.n8n.analyze(csv_path=csv_path, output_dir=output_dir, enrich_web=enrich_web)

    def run_direct(self, csv_path: str | None = None, output_dir: str | None = None, enrich_web: bool = True) -> dict:
        from analisar_leads import analyze

        return analyze(
            input_path=Path(csv_path or DEFAULT_INPUT_CSV),
            output_dir=Path(output_dir or OUTPUT_DIR),
            config_path=CONFIG_DIR / "nichos.json",
            enrich_web=enrich_web,
            max_enrich=30,
        )
