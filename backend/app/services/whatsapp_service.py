from __future__ import annotations

from typing import Any

from backend.app.config import N8N_WHATSAPP_SEND_WEBHOOK_URL


class WhatsAppService:
    def __init__(self, webhook_url: str = N8N_WHATSAPP_SEND_WEBHOOK_URL) -> None:
        self.webhook_url = webhook_url

    def send_via_n8n(
        self,
        lead: dict[str, Any],
        message: str,
        mode: str = "freeform",
        template_name: str | None = None,
        language_code: str = "pt_BR",
    ) -> dict[str, Any]:
        phone = normalize_phone(lead.get("telefone", ""))
        if not phone:
            raise ValueError("Lead sem telefone valido para WhatsApp.")

        payload = {
            "leadId": lead.get("lead_id"),
            "name": lead.get("nome"),
            "phone": phone,
            "message": message,
            "mode": mode,
            "templateName": template_name,
            "languageCode": language_code,
            "lead": lead,
            "source": "lobo-walstreet",
        }

        import httpx

        with httpx.Client(timeout=120) as client:
            response = client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            if not response.content:
                return {"ok": True}
            return response.json()


def normalize_phone(value: str) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if not digits:
        return ""
    if digits.startswith("55"):
        return digits
    return f"55{digits}"
