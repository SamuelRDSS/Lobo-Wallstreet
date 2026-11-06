from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import CRM_STATE_FILE
from backend.app.storage.database import OperationalDatabase


DEFAULT_STATUSES = [
    "Não abordado",
    "Pronto para envio",
    "Abordado",
    "Aguardando resposta",
    "Respondeu",
    "Resposta pendente",
    "Interessado",
    "Fechado",
    "Sem interesse",
]
WHATSAPP_SENT_STATUS = "Aguardando resposta"
WHATSAPP_REPLY_STATUS = "Resposta pendente"


def normalize_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "nao contatado": "Não abordado",
        "não contatado": "Não abordado",
        "nao abordado": "Não abordado",
        "não abordado": "Não abordado",
        "n?o abordado": "Não abordado",
        "chamado": "Abordado",
        "contatado": "Abordado",
        "enviado": "Aguardando resposta",
        "aguardando": "Aguardando resposta",
        "resposta pendente": "Resposta pendente",
        "pendente": "Resposta pendente",
        "proposta": "Interessado",
        "perdido": "Sem interesse",
    }
    if normalized in aliases:
        return aliases[normalized]
    for status in DEFAULT_STATUSES:
        if normalized == status.lower():
            return status
    return "Não abordado"


class CrmService:
    def __init__(self, state_file: Path = CRM_STATE_FILE) -> None:
        self.state_file = state_file
        self.database = OperationalDatabase()

    def load(self) -> dict:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, lead_id: str, status: str, notes: str = "") -> dict:
        state = self.load()
        current = state.get(lead_id, {})
        current.update({"status": normalize_status(status), "notes": notes})
        state[lead_id] = current
        self.save(state)
        self._sync_sqlite(lead_id, current)
        return state[lead_id]

    def record_whatsapp_sent(self, lead_id: str, message: str, provider_result: dict | None = None) -> dict:
        state = self.load()
        current = state.get(lead_id, {})
        current["status"] = WHATSAPP_SENT_STATUS
        current["last_whatsapp_message"] = message
        current["last_whatsapp_provider_result"] = provider_result or {}
        self._append_event(current, "whatsapp_sent", {"message": message, "provider_result": provider_result or {}})
        state[lead_id] = current
        self.save(state)
        self._sync_sqlite(lead_id, current)
        return current

    def record_whatsapp_reply(
        self,
        lead_id: str,
        phone: str,
        message: str,
        contact_name: str = "",
        provider_payload: dict | None = None,
    ) -> dict:
        state = self.load()
        current = state.get(lead_id, {})
        current["status"] = WHATSAPP_REPLY_STATUS
        current["last_reply_phone"] = phone
        current["last_reply_name"] = contact_name
        current["last_reply_message"] = message
        current["last_reply_provider_payload"] = provider_payload or {}
        current["reply_pending_approval"] = True
        self._append_event(
            current,
            "whatsapp_reply",
            {
                "phone": phone,
                "contact_name": contact_name,
                "message": message,
                "provider_payload": provider_payload or {},
            },
        )
        state[lead_id] = current
        self.save(state)
        self._sync_sqlite(lead_id, current)
        return current

    def record_ai_suggestion(self, lead_id: str, suggestion: str) -> dict:
        state = self.load()
        current = state.get(lead_id, {})
        current["ai_suggestion"] = suggestion
        current["pending_ai_reply"] = suggestion
        current["reply_pending_approval"] = True
        self._append_event(current, "ai_suggestion", {"suggestion": suggestion})
        state[lead_id] = current
        self.save(state)
        self._sync_sqlite(lead_id, current)
        return current

    def record_ai_reply_sent(self, lead_id: str, reply: str, provider_result: dict | None = None) -> dict:
        state = self.load()
        current = state.get(lead_id, {})
        current["status"] = WHATSAPP_SENT_STATUS
        current["reply_pending_approval"] = False
        current["last_ai_reply_sent"] = reply
        current["pending_ai_reply"] = ""
        current["last_whatsapp_provider_result"] = provider_result or {}
        self._append_event(current, "ai_reply_sent", {"reply": reply, "provider_result": provider_result or {}})
        state[lead_id] = current
        self.save(state)
        self._sync_sqlite(lead_id, current)
        return current

    def _append_event(self, current: dict[str, Any], event_type: str, payload: dict) -> None:
        history = current.setdefault("history", [])
        history.append({"type": event_type, "payload": payload})
        if len(history) > 50:
            del history[:-50]

    def _sync_sqlite(self, lead_id: str, current: dict[str, Any]) -> None:
        self.database.upsert_crm(
            lead_id=lead_id,
            status=current.get("status", ""),
            notes=current.get("notes", ""),
            payload=current,
        )
