from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from backend.app.config import LEADS_OUTPUT_CSV
from backend.app.services.crm_service import CrmService, normalize_status
from backend.app.services.message_service import generate_sales_message
from backend.app.utils.csv_utils import read_csv


class LeadRepository:
    def __init__(self, output_csv: Path = LEADS_OUTPUT_CSV, crm: CrmService | None = None) -> None:
        self.output_csv = output_csv
        self.crm = crm or CrmService()

    def list_leads(self) -> dict[str, Any]:
        rows = read_csv(self.output_csv)
        crm_state = self.crm.load()
        leads = [self._hydrate(row, crm_state) for row in rows]
        return {
            "leads": leads,
            "summary": self._summary(leads),
            "source": str(self.output_csv),
        }

    def _hydrate(self, row: dict[str, str], crm_state: dict) -> dict:
        lead = dict(row)
        lead_id = self._lead_id(lead)
        crm = crm_state.get(lead_id, {})
        lead["lead_id"] = lead_id
        lead["crm_status"] = self._normalize_status(crm.get("status") or lead.get("status"))
        lead["crm_notes"] = crm.get("notes") or lead.get("observacoes") or ""
        lead["crm_history"] = crm.get("history") or []
        lead["last_whatsapp_message"] = crm.get("last_whatsapp_message") or ""
        lead["last_reply_message"] = crm.get("last_reply_message") or ""
        lead["last_reply_name"] = crm.get("last_reply_name") or ""
        lead["ai_suggestion"] = crm.get("ai_suggestion") or ""
        lead["pending_ai_reply"] = crm.get("pending_ai_reply") or ""
        lead["reply_pending_approval"] = bool(crm.get("reply_pending_approval"))
        lead["last_ai_reply_sent"] = crm.get("last_ai_reply_sent") or ""
        lead["abordagem"] = generate_sales_message(lead)
        lead["score_num"] = self._to_int(lead.get("score"))
        return lead

    def _summary(self, leads: list[dict]) -> dict[str, Any]:
        by_presence: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for lead in leads:
            by_presence[lead.get("presenca_digital") or "Não informado"] = by_presence.get(lead.get("presenca_digital") or "Não informado", 0) + 1
            by_priority[lead.get("chance") or "Não informado"] = by_priority.get(lead.get("chance") or "Não informado", 0) + 1
            by_status[lead.get("crm_status") or "Não abordado"] = by_status.get(lead.get("crm_status") or "Não abordado", 0) + 1

        return {
            "total": len(leads),
            "sem_site": by_presence.get("Sem site", 0),
            "com_site": by_presence.get("Site proprio", 0),
            "so_rede_social": by_presence.get("So rede social", 0),
            "app_encontrado": by_presence.get("App Android encontrado", 0),
            "prioridade_alta": by_priority.get("Alta chance", 0),
            "by_presence": by_presence,
            "by_priority": by_priority,
            "by_status": by_status,
        }

    def _lead_id(self, lead: dict) -> str:
        raw = "|".join([
            lead.get("nome", ""),
            lead.get("telefone", ""),
            lead.get("cidade", ""),
            lead.get("endereco", ""),
        ])
        return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:16]

    def find_lead_id_by_phone(self, phone: str) -> str | None:
        wanted = self._phone_digits(phone)
        if not wanted:
            return None
        for lead in self.list_leads()["leads"]:
            lead_phone = self._phone_digits(lead.get("telefone", ""))
            if lead_phone and (lead_phone.endswith(wanted[-10:]) or wanted.endswith(lead_phone[-10:])):
                return lead.get("lead_id")
        return None

    def _to_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except ValueError:
            return 0

    def _normalize_status(self, value: Any) -> str:
        return normalize_status(str(value or ""))

    def _phone_digits(self, value: str) -> str:
        return "".join(char for char in str(value or "") if char.isdigit())
