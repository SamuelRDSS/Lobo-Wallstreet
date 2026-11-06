from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.config import DATABASE_FILE


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def normalize_phone(value: str) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if not digits:
        return ""
    if digits.startswith("55"):
        return digits
    return f"55{digits}"


def normalize_url(value: str) -> str:
    url = str(value or "").strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = url.removeprefix("www.")
    return url.rstrip("/")


def stable_lead_id(lead: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(lead.get("nome") or lead.get("name") or ""),
            str(lead.get("telefone") or lead.get("phone") or ""),
            str(lead.get("cidade") or lead.get("city") or ""),
            str(lead.get("endereco") or lead.get("address") or ""),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:16]


class OperationalDatabase:
    def __init__(self, db_path: Path = DATABASE_FILE) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    nome TEXT,
                    categoria TEXT,
                    cidade TEXT,
                    estado TEXT,
                    telefone TEXT,
                    website TEXT,
                    instagram TEXT,
                    endereco TEXT,
                    nota TEXT,
                    avaliacoes TEXT,
                    google_maps TEXT,
                    origem TEXT,
                    origem_id TEXT,
                    capturado_em TEXT,
                    duplicado INTEGER DEFAULT 0,
                    duplicate_of TEXT,
                    analisado_em TEXT,
                    raw_json TEXT
                );

                CREATE TABLE IF NOT EXISTS lead_keys (
                    key TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    lead_id TEXT,
                    duplicate_of TEXT,
                    origem TEXT,
                    origem_id TEXT,
                    captured_at TEXT,
                    payload_json TEXT
                );

                CREATE TABLE IF NOT EXISTS analysis (
                    lead_id TEXT PRIMARY KEY,
                    presenca_digital TEXT,
                    score INTEGER,
                    chance TEXT,
                    motivo TEXT,
                    url_detectada TEXT,
                    fonte_detectada TEXT,
                    titulo_detectado TEXT,
                    status_enriquecimento TEXT,
                    mensagem_gerada TEXT,
                    analyzed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS crm (
                    lead_id TEXT PRIMARY KEY,
                    status TEXT,
                    notas TEXT,
                    atualizado_em TEXT,
                    payload_json TEXT
                );
                """
            )
            for column in ["estado TEXT", "nota TEXT", "avaliacoes TEXT", "google_maps TEXT"]:
                try:
                    conn.execute(f"ALTER TABLE leads ADD COLUMN {column}")
                except sqlite3.OperationalError:
                    pass

    def upsert_collected_leads(self, leads: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
        captured_at = utc_now()
        inserted: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []

        with self.connect() as conn:
            for lead in leads:
                normalized = self._normalize_collected_lead(lead)
                keys = self.dedupe_keys(normalized)
                duplicate_of = self._find_existing_lead(conn, keys)

                if duplicate_of:
                    duplicates.append({**normalized, "duplicate_of": duplicate_of})
                    self._insert_raw(conn, run_id, normalized, captured_at, duplicate_of=duplicate_of)
                    continue

                lead_id = stable_lead_id(normalized)
                normalized["id"] = lead_id
                normalized["capturado_em"] = captured_at
                inserted.append(normalized)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO leads (
                        id, nome, categoria, cidade, estado, telefone, website, instagram, endereco,
                        nota, avaliacoes, google_maps, origem, origem_id, capturado_em, duplicado, duplicate_of, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                    """,
                    (
                        lead_id,
                        normalized.get("nome", ""),
                        normalized.get("categoria", ""),
                        normalized.get("cidade", ""),
                        normalized.get("estado", ""),
                        normalized.get("telefone", ""),
                        normalized.get("website", ""),
                        normalized.get("instagram", ""),
                        normalized.get("endereco", ""),
                        normalized.get("nota", ""),
                        normalized.get("avaliacoes", ""),
                        normalized.get("google_maps", ""),
                        normalized.get("origem", ""),
                        normalized.get("origem_id", ""),
                        captured_at,
                        json.dumps(normalized, ensure_ascii=False),
                    ),
                )
                for key in keys:
                    conn.execute("INSERT OR IGNORE INTO lead_keys (key, lead_id) VALUES (?, ?)", (key, lead_id))
                self._insert_raw(conn, run_id, normalized, captured_at, lead_id=lead_id)

        return {
            "run_id": run_id,
            "captured_at": captured_at,
            "received": len(leads),
            "inserted": len(inserted),
            "duplicates": len(duplicates),
            "new_leads": inserted,
            "duplicate_leads": duplicates,
        }

    def export_leads_csv(self, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.list_leads(include_analysis=False)
        fields = [
            "title",
            "totalScore",
            "reviewsCount",
            "street",
            "city",
            "state",
            "website",
            "phone",
            "categories/0",
            "url",
            "instagram",
            "source",
            "sourceId",
            "capturedAt",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "title": row.get("nome", ""),
                        "totalScore": row.get("nota", ""),
                        "reviewsCount": row.get("avaliacoes", ""),
                        "street": row.get("endereco", ""),
                        "city": row.get("cidade", ""),
                        "state": row.get("estado", ""),
                        "website": row.get("website", ""),
                        "phone": row.get("telefone", ""),
                        "categories/0": row.get("categoria", ""),
                        "url": row.get("google_maps", ""),
                        "instagram": row.get("instagram", ""),
                        "source": row.get("origem", ""),
                        "sourceId": row.get("origem_id", ""),
                        "capturedAt": row.get("capturado_em", ""),
                    }
                )
        return len(rows)

    def sync_analysis_from_csv(self, csv_path: Path) -> int:
        if not csv_path.exists():
            return 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        analyzed_at = utc_now()
        with self.connect() as conn:
            for row in rows:
                lead_id = stable_lead_id(row)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis (
                        lead_id, presenca_digital, score, chance, motivo, url_detectada,
                        fonte_detectada, titulo_detectado, status_enriquecimento,
                        mensagem_gerada, analyzed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead_id,
                        row.get("presenca_digital", ""),
                        self._to_int(row.get("score")),
                        row.get("chance", ""),
                        row.get("motivo", ""),
                        row.get("url_detectada", ""),
                        row.get("fonte_detectada", ""),
                        row.get("titulo_detectado", ""),
                        row.get("status_enriquecimento", ""),
                        row.get("mensagem_whatsapp", ""),
                        analyzed_at,
                    ),
                )
                conn.execute("UPDATE leads SET analisado_em = ? WHERE id = ?", (analyzed_at, lead_id))
        return len(rows)

    def upsert_crm(self, lead_id: str, status: str, notes: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crm (lead_id, status, notas, atualizado_em, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lead_id, status, notes, utc_now(), json.dumps(payload, ensure_ascii=False)),
            )

    def list_leads(self, include_analysis: bool = True) -> list[dict[str, Any]]:
        query = """
            SELECT
                l.*,
                a.presenca_digital,
                a.score,
                a.chance,
                a.motivo,
                a.url_detectada,
                a.fonte_detectada,
                a.titulo_detectado,
                a.status_enriquecimento,
                a.mensagem_gerada,
                c.status AS crm_status,
                c.notas AS crm_notes
            FROM leads l
            LEFT JOIN analysis a ON a.lead_id = l.id
            LEFT JOIN crm c ON c.lead_id = l.id
            ORDER BY COALESCE(a.score, 0) DESC, l.capturado_em DESC
        """
        if not include_analysis:
            query = "SELECT * FROM leads ORDER BY capturado_em DESC"
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(query).fetchall()]

    def queue_summary(self) -> dict[str, int]:
        rows = self.list_leads(include_analysis=True)
        return {
            "total": len(rows),
            "novos": sum(1 for row in rows if not row.get("analisado_em")),
            "analisados": sum(1 for row in rows if row.get("analisado_em")),
            "alta_prioridade": sum(1 for row in rows if row.get("chance") == "Alta chance"),
            "sem_telefone": sum(1 for row in rows if not row.get("telefone")),
            "ja_abordados": sum(1 for row in rows if row.get("crm_status") in {"Abordado", "Aguardando resposta", "Respondeu", "Resposta pendente", "Interessado"}),
            "ignorados": sum(1 for row in rows if row.get("crm_status") == "Sem interesse"),
            "fechados": sum(1 for row in rows if row.get("crm_status") == "Fechado"),
        }

    def dedupe_keys(self, lead: dict[str, Any]) -> list[str]:
        keys: list[str] = []
        source = normalize_text(lead.get("origem", ""))
        source_id = normalize_text(lead.get("origem_id", ""))
        phone = normalize_phone(lead.get("telefone", ""))
        website = normalize_url(lead.get("website", ""))
        name_address = normalize_text(
            " ".join([lead.get("nome", ""), lead.get("endereco", ""), lead.get("cidade", "")])
        )
        if source and source_id:
            keys.append(f"source:{source}:{source_id}")
        if phone:
            keys.append(f"phone:{phone}")
        if website:
            keys.append(f"website:{website}")
        if name_address:
            keys.append(f"name_address:{name_address}")
        return keys

    def _normalize_collected_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        return {
            "nome": str(lead.get("nome") or lead.get("name") or "").strip(),
            "categoria": str(lead.get("categoria") or lead.get("category") or "").strip(),
            "cidade": str(lead.get("cidade") or lead.get("city") or "").strip(),
            "estado": str(lead.get("estado") or lead.get("state") or "").strip(),
            "telefone": str(lead.get("telefone") or lead.get("phone") or "").strip(),
            "website": str(lead.get("website") or lead.get("site") or "").strip(),
            "instagram": str(lead.get("instagram") or "").strip(),
            "endereco": str(lead.get("endereco") or lead.get("address") or "").strip(),
            "origem": str(lead.get("origem") or lead.get("source") or "mock").strip(),
            "origem_id": str(lead.get("origem_id") or lead.get("source_id") or lead.get("place_id") or "").strip(),
            "google_maps": str(lead.get("google_maps") or lead.get("maps_url") or "").strip(),
            "nota": str(lead.get("nota") or lead.get("rating") or "").strip(),
            "avaliacoes": str(lead.get("avaliacoes") or lead.get("reviews") or "").strip(),
            "raw": lead,
        }

    def _find_existing_lead(self, conn: sqlite3.Connection, keys: list[str]) -> str | None:
        for key in keys:
            row = conn.execute("SELECT lead_id FROM lead_keys WHERE key = ?", (key,)).fetchone()
            if row:
                return str(row["lead_id"])
        return None

    def _insert_raw(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        lead: dict[str, Any],
        captured_at: str,
        lead_id: str | None = None,
        duplicate_of: str | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO raw_leads (run_id, lead_id, duplicate_of, origem, origem_id, captured_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                lead_id,
                duplicate_of,
                lead.get("origem", ""),
                lead.get("origem_id", ""),
                captured_at,
                json.dumps(lead, ensure_ascii=False),
            ),
        )

    def _to_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except ValueError:
            return 0
