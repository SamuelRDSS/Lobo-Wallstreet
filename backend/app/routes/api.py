from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    AiDraftRequest,
    AnalyzeRequest,
    CollectRequest,
    CrmUpdateRequest,
    MessageRequest,
    WhatsAppInboundRequest,
    WhatsAppReplySendRequest,
    WhatsAppSendRequest,
)
from backend.app.config import LEADS_OUTPUT_CSV, N8N_WEBHOOK_URL, N8N_WHATSAPP_SEND_WEBHOOK_URL, WHATSAPP_INBOUND_TOKEN
from backend.app.services.analyzer_service import AnalyzerService
from backend.app.services.ai_service import draft_sales_reply
from backend.app.services.collector_service import CollectorService
from backend.app.services.crm_service import CrmService, DEFAULT_STATUSES
from backend.app.services.lead_repository import LeadRepository
from backend.app.services.message_service import generate_sales_message
from backend.app.services.whatsapp_service import WhatsAppService


router = APIRouter(prefix="/api")
analyzer = AnalyzerService()
crm = CrmService()
repository = LeadRepository(crm=crm)
whatsapp = WhatsAppService()
collector = CollectorService()


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "name": "Lobo Walstreet",
        "n8nWebhook": N8N_WEBHOOK_URL,
        "n8nWhatsAppWebhook": N8N_WHATSAPP_SEND_WEBHOOK_URL,
        "outputCsv": str(LEADS_OUTPUT_CSV),
    }


@router.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    try:
        if request.prefer_n8n:
            result = analyzer.run_via_n8n(
                csv_path=request.csv_path,
                output_dir=request.output_dir,
                enrich_web=request.enrich_web,
            )
        else:
            result = analyzer.run_direct(
                csv_path=request.csv_path,
                output_dir=request.output_dir,
                enrich_web=request.enrich_web,
            )
        if isinstance(result, dict) and result.get("ok") is False:
            raise RuntimeError(str(result.get("error") or result.get("results") or "n8n retornou falha"))
        synced = collector.database.sync_analysis_from_csv(LEADS_OUTPUT_CSV)
        return {"ok": True, "result": result, "summary": repository.list_leads().get("summary", {}), "syncedAnalysisRows": synced}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/collect")
def collect(request: CollectRequest) -> dict:
    try:
        return collector.collect(
            niche=request.nicho,
            city=request.cidade,
            limit=request.limite,
            provider_name=request.provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/collect-and-analyze")
def collect_and_analyze(request: CollectRequest) -> dict:
    try:
        return collector.collect_and_analyze(
            niche=request.nicho,
            city=request.cidade,
            limit=request.limite,
            provider_name=request.provider,
            prefer_n8n=request.prefer_n8n,
            enrich_web=request.enrich_web,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/pipeline")
def pipeline() -> dict:
    return {"ok": True, "queue": collector.queue_summary(), "leads": collector.list_operational_leads()}


@router.get("/leads")
def leads() -> dict:
    return {"ok": True, **repository.list_leads()}


@router.get("/crm/statuses")
def crm_statuses() -> dict:
    return {"ok": True, "statuses": DEFAULT_STATUSES}


@router.post("/crm")
def update_crm(request: CrmUpdateRequest) -> dict:
    return {"ok": True, "crm": crm.update(request.lead_id, request.status, request.notes)}


@router.post("/message")
def message(request: MessageRequest) -> dict:
    return {"ok": True, "message": generate_sales_message(request.lead)}


@router.post("/whatsapp/send")
def send_whatsapp(request: WhatsAppSendRequest) -> dict:
    if not request.approved:
        raise HTTPException(status_code=400, detail="Envio bloqueado: confirme approved=true.")

    lead = request.lead
    lead_id = lead.get("lead_id")
    if not lead_id:
        raise HTTPException(status_code=400, detail="Lead sem lead_id.")

    message_text = request.message or lead.get("abordagem") or generate_sales_message(lead)
    try:
        result = whatsapp.send_via_n8n(
            lead=lead,
            message=message_text,
            mode=request.mode,
            template_name=request.template_name,
            language_code=request.language_code,
        )
        crm_state = crm.record_whatsapp_sent(lead_id, message_text, result)
        return {"ok": True, "result": result, "crm": crm_state}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/whatsapp/send-reply")
def send_whatsapp_reply(request: WhatsAppReplySendRequest) -> dict:
    if not request.approved:
        raise HTTPException(status_code=400, detail="Resposta bloqueada: confirme approved=true.")

    lead = request.lead
    lead_id = lead.get("lead_id")
    if not lead_id:
        raise HTTPException(status_code=400, detail="Lead sem lead_id.")

    reply_text = (request.reply or "").strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="Resposta vazia.")

    try:
        result = whatsapp.send_via_n8n(
            lead=lead,
            message=reply_text,
            mode=request.mode,
        )
        crm_state = crm.record_ai_reply_sent(lead_id, reply_text, result)
        return {"ok": True, "result": result, "crm": crm_state}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/whatsapp/inbound")
def receive_whatsapp_reply(request: WhatsAppInboundRequest) -> dict:
    if WHATSAPP_INBOUND_TOKEN and request.token != WHATSAPP_INBOUND_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalido para webhook de WhatsApp.")

    phone = request.phone or request.from_phone or ""
    lead_id = request.lead_id or repository.find_lead_id_by_phone(phone)
    if not lead_id:
        raise HTTPException(status_code=404, detail="Nao encontrei lead para esse telefone.")

    lead = next((item for item in repository.list_leads()["leads"] if item.get("lead_id") == lead_id), {})
    crm_state = crm.record_whatsapp_reply(
        lead_id=lead_id,
        phone=phone,
        message=request.message,
        contact_name=request.contact_name or "",
        provider_payload=request.provider_payload or {},
    )
    suggestion = draft_sales_reply(lead, request.message)
    crm_state = crm.record_ai_suggestion(lead_id, suggestion)
    return {
        "ok": True,
        "leadId": lead_id,
        "crm": crm_state,
        "aiSuggestion": suggestion,
        "requiresConfirmation": True,
    }


@router.post("/ai/draft-reply")
def ai_draft_reply(request: AiDraftRequest) -> dict:
    return {"ok": True, "reply": draft_sales_reply(request.lead, request.incoming_message)}
