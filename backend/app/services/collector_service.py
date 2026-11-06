from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from backend.app.collectors.base import LeadProvider
from backend.app.collectors.google_places import GooglePlacesProvider
from backend.app.collectors.mock_provider import MockLeadProvider
from backend.app.config import COLLECTED_INPUT_CSV, LEADS_OUTPUT_CSV, OUTPUT_DIR, RAW_LEADS_DIR
from backend.app.services.analyzer_service import AnalyzerService
from backend.app.storage.database import OperationalDatabase, utc_now


class CollectorService:
    def __init__(self, database: OperationalDatabase | None = None) -> None:
        self.database = database or OperationalDatabase()
        self.analyzer = AnalyzerService()
        self.providers: dict[str, LeadProvider] = {
            "mock": MockLeadProvider(),
            "google_places": GooglePlacesProvider(),
        }

    def collect(self, niche: str, city: str, limit: int = 30, provider_name: str = "mock") -> dict[str, Any]:
        provider = self._provider(provider_name)
        run_id = f"collect-{uuid.uuid4().hex[:12]}"
        raw_leads = [lead.to_dict() for lead in provider.search(niche, city, limit)]
        self._write_raw_jsonl(run_id, provider.name, raw_leads)
        result = self.database.upsert_collected_leads(raw_leads, run_id)
        exported_count = self.database.export_leads_csv(COLLECTED_INPUT_CSV)
        return {
            "ok": True,
            "provider": provider.name,
            "nicho": niche,
            "cidade": city,
            "limite": limit,
            "inputCsv": str(COLLECTED_INPUT_CSV),
            "exportedToCsv": exported_count,
            **result,
            "queue": self.database.queue_summary(),
        }

    def collect_and_analyze(
        self,
        niche: str,
        city: str,
        limit: int = 30,
        provider_name: str = "mock",
        prefer_n8n: bool = False,
        enrich_web: bool = True,
    ) -> dict[str, Any]:
        collection = self.collect(niche, city, limit, provider_name)
        if prefer_n8n:
            analysis_result = self.analyzer.run_via_n8n(
                csv_path=str(COLLECTED_INPUT_CSV),
                output_dir=str(OUTPUT_DIR),
                enrich_web=enrich_web,
            )
        else:
            analysis_result = self.analyzer.run_direct(
                csv_path=str(COLLECTED_INPUT_CSV),
                output_dir=str(OUTPUT_DIR),
                enrich_web=enrich_web,
            )
        synced = self.database.sync_analysis_from_csv(LEADS_OUTPUT_CSV)
        return {
            "ok": True,
            "collection": collection,
            "analysis": analysis_result,
            "syncedAnalysisRows": synced,
            "queue": self.database.queue_summary(),
        }

    def queue_summary(self) -> dict[str, int]:
        return self.database.queue_summary()

    def list_operational_leads(self) -> list[dict[str, Any]]:
        return self.database.list_leads(include_analysis=True)

    def _provider(self, name: str) -> LeadProvider:
        provider = self.providers.get((name or "mock").strip().lower())
        if not provider:
            available = ", ".join(sorted(self.providers))
            raise ValueError(f"Provider '{name}' nao encontrado. Disponiveis: {available}.")
        return provider

    def _write_raw_jsonl(self, run_id: str, provider_name: str, raw_leads: list[dict[str, Any]]) -> Path:
        RAW_LEADS_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_LEADS_DIR / f"{run_id}-{provider_name}.jsonl"
        captured_at = utc_now()
        with path.open("w", encoding="utf-8") as file:
            for lead in raw_leads:
                file.write(json.dumps({"captured_at": captured_at, "lead": lead}, ensure_ascii=False) + "\n")
        return path
