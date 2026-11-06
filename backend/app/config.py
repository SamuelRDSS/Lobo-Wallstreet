from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(
    os.environ.get("LOBO_ROOT") or Path(__file__).resolve().parents[2]
)

IS_VERCEL = os.environ.get("VERCEL") == "1"
RUNTIME_DATA_ROOT = Path(
    os.environ.get("LOBO_DATA_DIR")
    or ("/tmp/lobo-walstreet" if IS_VERCEL else PROJECT_ROOT)
)

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = RUNTIME_DATA_ROOT / "dados"
INPUT_DIR = DATA_DIR / "entrada"
CRM_DIR = DATA_DIR / "crm"
RAW_LEADS_DIR = DATA_DIR / "brutos"
OUTPUT_DIR = RUNTIME_DATA_ROOT / "saida"
FRONT_DIR = PROJECT_ROOT / "front"
N8N_DIR = PROJECT_ROOT / "n8n"

DEFAULT_INPUT_CSV = INPUT_DIR / "google_places_barbearias_sao_jose.csv"
COLLECTED_INPUT_CSV = INPUT_DIR / "leads_coletados.csv"
LEGACY_INPUT_CSV = PROJECT_ROOT / "dataset_crawler-google-places_2026-04-17_01-37-43-265.csv"
LEADS_OUTPUT_CSV = OUTPUT_DIR / "leads_priorizados.csv"
CRM_STATE_FILE = CRM_DIR / "crm_status.json"
DATABASE_FILE = DATA_DIR / "lobo_walstreet.sqlite3"
ANALYZER_SCRIPT = PROJECT_ROOT / "analisar_leads.py"

N8N_WEBHOOK_URL = os.environ.get(
    "LOBO_N8N_WEBHOOK_URL",
    "http://localhost:5678/webhook/lead-site-analyzer-webhook/webhook-csv/analisar-leads-sites",
)
N8N_WHATSAPP_SEND_WEBHOOK_URL = os.environ.get(
    "LOBO_N8N_WHATSAPP_SEND_WEBHOOK_URL",
    "http://localhost:5678/webhook/lobo-whatsapp/send",
)
WHATSAPP_INBOUND_TOKEN = os.environ.get("LOBO_WHATSAPP_INBOUND_TOKEN", "")


def ensure_directories() -> None:
    for path in [INPUT_DIR, CRM_DIR, RAW_LEADS_DIR, OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
