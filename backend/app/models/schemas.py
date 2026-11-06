from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    csv_path: str | None = Field(default=None, alias="csvPath")
    output_dir: str | None = Field(default=None, alias="outputDir")
    enrich_web: bool = Field(default=True, alias="enrichWeb")
    prefer_n8n: bool = Field(default=True, alias="preferN8n")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class CollectRequest(BaseModel):
    nicho: str
    cidade: str
    limite: int = 30
    provider: str = "mock"
    prefer_n8n: bool = Field(default=False, alias="preferN8n")
    enrich_web: bool = Field(default=True, alias="enrichWeb")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class CrmUpdateRequest(BaseModel):
    lead_id: str = Field(alias="leadId")
    status: str
    notes: str = ""

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class MessageRequest(BaseModel):
    lead: dict[str, Any]


class WhatsAppSendRequest(BaseModel):
    lead: dict[str, Any]
    message: str | None = None
    approved: bool = False
    mode: str = "freeform"
    template_name: str | None = Field(default=None, alias="templateName")
    language_code: str = Field(default="pt_BR", alias="languageCode")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class WhatsAppReplySendRequest(BaseModel):
    lead: dict[str, Any]
    reply: str
    approved: bool = False
    mode: str = "freeform"


class WhatsAppInboundRequest(BaseModel):
    lead_id: str | None = Field(default=None, alias="leadId")
    phone: str | None = None
    from_phone: str | None = Field(default=None, alias="from")
    contact_name: str | None = Field(default=None, alias="contactName")
    message: str = ""
    token: str | None = None
    provider_payload: dict[str, Any] | None = Field(default=None, alias="providerPayload")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class AiDraftRequest(BaseModel):
    lead: dict[str, Any]
    incoming_message: str = Field(alias="incomingMessage")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class ApiResponse(BaseModel):
    ok: bool
    data: Any | None = None
    error: str | None = None
