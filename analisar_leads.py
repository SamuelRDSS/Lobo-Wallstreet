#!/usr/bin/env python3
"""Lead analyzer for local businesses exported from Google Places-like CSVs.

The project uses small "agents" as isolated decision steps:
column mapping, digital presence detection, niche detection, scoring,
message generation and exporting.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config" / "nichos.json"
DEFAULT_OUTPUT_DIR = ROOT / "saida"


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def normalize_key(value: str) -> str:
    value = strip_accents(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip().replace(",", ".")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    text = re.sub(r"[^0-9-]", "", str(value))
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                sample = file.read(4096)
                file.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
                except csv.Error:
                    dialect = csv.excel
                rows = list(csv.DictReader(file, dialect=dialect))
                return rows, encoding
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"Nao consegui ler o CSV {path}: {last_error}")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def domain_from_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if not re.match(r"^[a-z]+://", text, re.I):
        text = "https://" + text
    parsed = urlparse(text)
    domain = parsed.netloc.lower()
    if "@" in domain:
        domain = domain.rsplit("@", 1)[-1]
    domain = domain.split(":")[0]
    return domain[4:] if domain.startswith("www.") else domain


def domain_matches(domain: str, candidates: list[str]) -> bool:
    for candidate in candidates:
        candidate = candidate.lower()
        if domain == candidate or domain.endswith("." + candidate):
            return True
    return False


def digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def whatsapp_number(phone: str, default_country_code: str = "55") -> str:
    digits = digits_only(phone)
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith(default_country_code):
        return digits
    if len(digits) in (10, 11):
        return default_country_code + digits
    return digits


@dataclass
class Lead:
    raw: dict[str, str]
    mapped: dict[str, str]
    reasons: list[str] = field(default_factory=list)
    score: int = 0
    chance: str = ""
    presence_type: str = ""
    presence_label: str = ""
    niche_key: str = "negocio_local"
    niche_label: str = "Negocio local"
    offer: str = ""
    message: str = ""
    whatsapp_url: str = ""
    detected_url: str = ""
    detected_source: str = ""
    detected_title: str = ""
    enrichment_status: str = "nao consultado"


class ColumnMapperAgent:
    aliases = {
        "title": "name",
        "nome": "name",
        "empresa": "name",
        "business_name": "name",
        "name": "name",
        "totalscore": "rating",
        "nota": "rating",
        "rating": "rating",
        "score": "rating",
        "reviewscount": "reviews",
        "reviews": "reviews",
        "reviews_count": "reviews",
        "avaliacoes": "reviews",
        "quantidade_de_avaliacoes": "reviews",
        "street": "address",
        "endereco": "address",
        "address": "address",
        "city": "city",
        "cidade": "city",
        "state": "state",
        "estado": "state",
        "website": "website",
        "site": "website",
        "url_site": "website",
        "phone": "phone",
        "telefone": "phone",
        "whatsapp": "phone",
        "url": "maps_url",
        "google_maps": "maps_url",
        "maps": "maps_url",
        "categoryname": "category",
        "category_name": "category",
        "categoria": "category",
        "categories_0": "category",
        "categories_1": "category_extra_1",
        "categories_2": "category_extra_2",
        "categories_3": "category_extra_3"
    }

    canonical_fields = [
        "name", "rating", "reviews", "address", "city", "state", "website",
        "phone", "category", "category_extra_1", "category_extra_2",
        "category_extra_3", "maps_url"
    ]

    def detect_mapping(self, rows: list[dict[str, str]]) -> dict[str, str]:
        if not rows:
            return {}
        headers = rows[0].keys()
        mapping: dict[str, str] = {}
        for header in headers:
            normalized = normalize_key(header)
            canonical = self.aliases.get(normalized)
            if canonical and canonical not in mapping:
                mapping[canonical] = header
        return mapping

    def map_row(self, row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for field_name in self.canonical_fields:
            source = mapping.get(field_name)
            mapped[field_name] = (row.get(source, "") if source else "").strip()
        return mapped


class PresenceAgent:
    labels = {
        "sem_site": "Sem site",
        "so_rede_social": "So rede social",
        "link_na_bio": "Link na bio",
        "google_sites": "Google Sites",
        "plataforma_agendamento": "Plataforma de agendamento",
        "marketplace_perfil": "Marketplace/perfil de terceiros",
        "app_mobile": "App Android encontrado",
        "construtor_simples": "Construtor simples",
        "site_proprio": "Site proprio",
        "site_informado": "Site informado"
    }

    def __init__(self, config: dict[str, Any]) -> None:
        self.domains = config.get("presence_domains", {})

    def classify(self, lead: Lead) -> None:
        website = lead.mapped.get("website", "")
        domain = domain_from_url(website)
        if not website:
            lead.presence_type = "sem_site"
            lead.presence_label = self.labels[lead.presence_type]
            lead.reasons.append("nao tem site informado")
            return

        checks = [
            ("social", "so_rede_social", "usa rede social como site"),
            ("link_hub", "link_na_bio", "usa link na bio"),
            ("google_sites", "google_sites", "usa Google Sites"),
            ("booking", "plataforma_agendamento", "usa plataforma de agendamento"),
            ("marketplace", "marketplace_perfil", "usa marketplace/perfil de terceiros"),
            ("simple_builder", "construtor_simples", "usa construtor simples")
        ]
        for group, presence_type, reason in checks:
            if domain_matches(domain, self.domains.get(group, [])):
                lead.presence_type = presence_type
                lead.presence_label = self.labels[presence_type]
                lead.reasons.append(reason)
                return

        if domain:
            lead.presence_type = "site_proprio"
            lead.presence_label = self.labels[lead.presence_type]
            lead.reasons.append("ja tem dominio/site proprio")
        else:
            lead.presence_type = "site_informado"
            lead.presence_label = self.labels[lead.presence_type]
            lead.reasons.append("tem site informado, mas dominio nao foi identificado")


class WebEnrichmentAgent:
    """Finds public app evidence when the source CSV has no website."""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def enrich(self, lead: Lead) -> None:
        if lead.presence_type not in {"sem_site", "site_informado"}:
            lead.enrichment_status = "nao necessario"
            return

        name = lead.mapped.get("name", "")
        if not name:
            lead.enrichment_status = "sem nome"
            return

        try:
            app = self._search_google_play(name)
        except Exception as exc:
            lead.enrichment_status = f"erro: {exc}"
            return

        if not app:
            lead.enrichment_status = "nada encontrado"
            return

        lead.presence_type = "app_mobile"
        lead.presence_label = "App Android encontrado"
        lead.detected_url = app["url"]
        lead.detected_source = "Google Play"
        lead.detected_title = app["title"]
        lead.enrichment_status = "encontrado"
        developer = f" por {app['developer']}" if app.get("developer") else ""
        lead.reasons = [reason for reason in lead.reasons if reason != "nao tem site informado"]
        lead.reasons.append(f"app encontrado no Google Play: {app['title']}{developer}")

    def _search_google_play(self, business_name: str) -> dict[str, str] | None:
        url = "https://play.google.com/store/search?" + urlencode({"q": business_name, "c": "apps"})
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=self.timeout) as response:
            text = response.read().decode("utf-8", "ignore")

        pattern = re.compile(
            r'<a href="/store/apps/details\?id=([^"]+)" aria-label="([^"]+)"',
            re.I
        )
        for match in pattern.finditer(text):
            package_id = match.group(1)
            title = html.unescape(match.group(2)).strip()
            if not self._names_match(business_name, title):
                continue
            window = text[match.start(): match.start() + 1600]
            developer_match = re.search(r'<div class="LbQbAe">([^<]+)</div>', window)
            developer = html.unescape(developer_match.group(1)).strip() if developer_match else ""
            return {
                "title": title,
                "developer": developer,
                "url": f"https://play.google.com/store/apps/details?id={package_id}"
            }
        return None

    def _names_match(self, business_name: str, app_title: str) -> bool:
        business = normalize_for_match(business_name)
        title = normalize_for_match(app_title)
        if not business or not title:
            return False
        if business in title or title in business:
            return True
        business_tokens = {token for token in business.split() if len(token) > 2}
        title_tokens = {token for token in title.split() if len(token) > 2}
        if not business_tokens:
            return False
        return len(business_tokens & title_tokens) / len(business_tokens) >= 0.7


class NicheAgent:
    def __init__(self, config: dict[str, Any]) -> None:
        self.niches = config.get("niches", {})

    def classify(self, lead: Lead) -> None:
        text = " ".join([
            lead.mapped.get("category", ""),
            lead.mapped.get("category_extra_1", ""),
            lead.mapped.get("category_extra_2", ""),
            lead.mapped.get("category_extra_3", ""),
            lead.mapped.get("name", "")
        ])
        normalized = strip_accents(text).lower()

        for key, data in self.niches.items():
            if key == "negocio_local":
                continue
            for keyword in data.get("keywords", []):
                if strip_accents(keyword).lower() in normalized:
                    lead.niche_key = key
                    lead.niche_label = key.replace("_", " ").title()
                    lead.offer = data.get("offer", "")
                    return

        fallback = self.niches.get("negocio_local", {})
        lead.niche_key = "negocio_local"
        lead.niche_label = "Negocio Local"
        lead.offer = fallback.get("offer", "")


class ScoringAgent:
    def __init__(self, config: dict[str, Any]) -> None:
        self.weights = config.get("score_weights", {})
        self.niches = config.get("niches", {})

    def score(self, lead: Lead) -> None:
        score = int(self.weights.get("base", 20))
        presence_points = self.weights.get("presence", {}).get(lead.presence_type, 0)
        score += int(presence_points)

        phone = lead.mapped.get("phone", "")
        if phone:
            score += int(self.weights.get("phone_present", 10))
            lead.reasons.append("tem telefone para contato")
        else:
            score += int(self.weights.get("phone_missing", -12))
            lead.reasons.append("nao tem telefone no arquivo")

        reviews = safe_int(lead.mapped.get("reviews"))
        for rule in self.weights.get("reviews", []):
            if reviews >= int(rule.get("min", 0)):
                score += int(rule.get("points", 0))
                lead.reasons.append(f"{reviews} avaliacoes no Google")
                break

        rating = safe_float(lead.mapped.get("rating"))
        low_penalty = self.weights.get("rating_low_penalty", {})
        if rating and rating <= float(low_penalty.get("max", 0)):
            score += int(low_penalty.get("points", 0))
            lead.reasons.append(f"nota baixa ({rating:g})")
        else:
            for rule in self.weights.get("rating", []):
                if rating >= float(rule.get("min", 0)):
                    score += int(rule.get("points", 0))
                    lead.reasons.append(f"nota alta ({rating:g})")
                    break

        niche_data = self.niches.get(lead.niche_key, {})
        if niche_data.get("local_intent", True):
            score += int(self.weights.get("local_intent_bonus", 0))
            lead.reasons.append("negocio local depende de busca e contato rapido")

        lead.score = clamp(round(score))
        lead.chance = self._chance_label(lead)

    def _chance_label(self, lead: Lead) -> str:
        no_phone = not lead.mapped.get("phone")
        if no_phone and lead.score < 55:
            return "Dificil contato"
        if lead.score >= 75:
            return "Alta chance"
        if lead.score >= 50:
            return "Media chance"
        if lead.score >= 30:
            return "Baixa chance"
        return "Nao priorizar"


class MessageAgent:
    def make(self, lead: Lead) -> None:
        name = lead.mapped.get("name") or "sua empresa"
        city = lead.mapped.get("city") or "sua cidade"
        rating = lead.mapped.get("rating")
        reviews = safe_int(lead.mapped.get("reviews"))
        proof = ""
        if rating and reviews:
            proof = f" Vi tambem que voces tem nota {rating} e {reviews} avaliacoes, o que e uma prova social forte."
        elif rating:
            proof = f" Vi tambem que voces tem nota {rating}, o que ajuda muito na confianca."

        detected = ""
        if lead.presence_type == "app_mobile":
            detected = (
                " Vi que voces tambem tem app, entao a oportunidade pode ser um site com dominio proprio "
                "para aparecer melhor nas buscas e levar o cliente para o app ou WhatsApp."
            )

        message = (
            f"Ola, tudo bem? Vi a {name} no Google em {city}.{proof} "
            f"Notei que a presenca online hoje parece ser: {lead.presence_label}. "
            f"{detected} Eu monto {lead.offer}. Posso te mostrar um exemplo rapido?"
        )
        lead.message = re.sub(r"\s+", " ", message).strip()

        number = whatsapp_number(lead.mapped.get("phone", ""))
        if number:
            lead.whatsapp_url = f"https://wa.me/{number}?text={quote(lead.message)}"
        else:
            lead.whatsapp_url = ""


class ExportAgent:
    output_fields = [
        "rank",
        "chance",
        "score",
        "status",
        "nome",
        "nicho",
        "categoria_original",
        "cidade",
        "estado",
        "nota",
        "avaliacoes",
        "telefone",
        "whatsapp_url",
        "website",
        "presenca_digital",
        "url_detectada",
        "fonte_detectada",
        "titulo_detectado",
        "status_enriquecimento",
        "motivo",
        "oferta_sugerida",
        "mensagem_whatsapp",
        "google_maps",
        "endereco",
        "observacoes"
    ]

    chance_files = {
        "Alta chance": "leads_alta_chance.csv",
        "Media chance": "leads_media_chance.csv",
        "Baixa chance": "leads_baixa_chance.csv",
        "Dificil contato": "leads_dificil_contato.csv",
        "Nao priorizar": "leads_nao_priorizar.csv"
    }

    def export(self, leads: list[Lead], output_dir: Path, source_path: Path, encoding: str) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        sorted_leads = sorted(leads, key=lambda lead: (-lead.score, lead.mapped.get("name", "")))
        rows = [self._row(index + 1, lead) for index, lead in enumerate(sorted_leads)]

        all_csv = output_dir / "leads_priorizados.csv"
        write_csv(all_csv, rows, self.output_fields)

        grouped_paths: dict[str, str] = {}
        for chance, filename in self.chance_files.items():
            group_rows = [row for row in rows if row["chance"] == chance]
            if not group_rows:
                continue
            path = output_dir / filename
            write_csv(path, group_rows, self.output_fields)
            grouped_paths[chance] = str(path)

        summary = self._summary(sorted_leads, source_path, encoding)
        html_path = output_dir / "resumo_leads.html"
        html_path.write_text(self._html(summary, rows), encoding="utf-8")

        manifest = {
            "ok": True,
            "source_file": str(source_path),
            "source_encoding": encoding,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_leads": len(leads),
            "summary": summary,
            "outputs": {
                "all_csv": str(all_csv),
                "html_report": str(html_path),
                "groups": grouped_paths
            }
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["outputs"]["manifest"] = str(manifest_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def _row(self, rank: int, lead: Lead) -> dict[str, Any]:
        return {
            "rank": rank,
            "chance": lead.chance,
            "score": lead.score,
            "status": "Nao contatado",
            "nome": lead.mapped.get("name", ""),
            "nicho": lead.niche_label,
            "categoria_original": lead.mapped.get("category", ""),
            "cidade": lead.mapped.get("city", ""),
            "estado": lead.mapped.get("state", ""),
            "nota": lead.mapped.get("rating", ""),
            "avaliacoes": lead.mapped.get("reviews", ""),
            "telefone": lead.mapped.get("phone", ""),
            "whatsapp_url": lead.whatsapp_url,
            "website": lead.mapped.get("website", ""),
            "presenca_digital": lead.presence_label,
            "url_detectada": lead.detected_url,
            "fonte_detectada": lead.detected_source,
            "titulo_detectado": lead.detected_title,
            "status_enriquecimento": lead.enrichment_status,
            "motivo": "; ".join(dict.fromkeys(lead.reasons)),
            "oferta_sugerida": lead.offer,
            "mensagem_whatsapp": lead.message,
            "google_maps": lead.mapped.get("maps_url", ""),
            "endereco": lead.mapped.get("address", ""),
            "observacoes": ""
        }

    def _summary(self, leads: list[Lead], source_path: Path, encoding: str) -> dict[str, Any]:
        scores = [lead.score for lead in leads]
        by_chance: dict[str, int] = {}
        by_presence: dict[str, int] = {}
        for lead in leads:
            by_chance[lead.chance] = by_chance.get(lead.chance, 0) + 1
            by_presence[lead.presence_label] = by_presence.get(lead.presence_label, 0) + 1
        return {
            "source_file": str(source_path),
            "source_encoding": encoding,
            "total": len(leads),
            "average_score": round(statistics.mean(scores), 1) if scores else 0,
            "by_chance": by_chance,
            "by_presence": by_presence
        }

    def _html(self, summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
        top_rows = rows[:150]
        chance_cards = "".join(
            f"<div class='metric'><strong>{html.escape(key)}</strong><span>{value}</span></div>"
            for key, value in summary["by_chance"].items()
        )
        table_rows = "\n".join(self._html_row(row) for row in top_rows)
        return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resumo de Leads</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2328;
      --muted: #5f6b73;
      --line: #d8dee4;
      --bg: #f6f8fa;
      --surface: #ffffff;
      --good: #12783c;
      --mid: #8a6400;
      --bad: #9b2c2c;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 15px/1.45 Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 28px 24px 16px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
    }}
    main {{ padding: 20px 24px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ margin: 0; color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 18px 0 20px;
    }}
    .metric {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric strong {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric span {{ display: block; margin-top: 6px; font-size: 26px; font-weight: 700; }}
    .table-wrap {{
      overflow-x: auto;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1120px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: #eef2f3; font-size: 13px; }}
    .score {{ font-weight: 700; }}
    .alta {{ color: var(--good); font-weight: 700; }}
    .media {{ color: var(--mid); font-weight: 700; }}
    .baixa, .dificil, .nao {{ color: var(--bad); font-weight: 700; }}
    a.button {{
      display: inline-block;
      margin: 0 6px 6px 0;
      padding: 6px 8px;
      border-radius: 8px;
      color: #ffffff;
      background: var(--accent);
      text-decoration: none;
      white-space: nowrap;
    }}
    .small {{ color: var(--muted); font-size: 13px; max-width: 420px; }}
  </style>
</head>
<body>
  <header>
    <h1>Resumo de Leads</h1>
    <p>Arquivo: {html.escape(Path(summary["source_file"]).name)} | Total: {summary["total"]} | Score medio: {summary["average_score"]}</p>
  </header>
  <main>
    <section class="metrics">
      {chance_cards}
    </section>
    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Chance</th>
            <th>Score</th>
            <th>Empresa</th>
            <th>Cidade</th>
            <th>Presenca</th>
            <th>Motivo</th>
            <th>Acoes</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""

    def _html_row(self, row: dict[str, Any]) -> str:
        chance_class = normalize_key(row["chance"]).split("_")[0]
        actions = []
        if row.get("whatsapp_url"):
            actions.append(f"<a class='button' href='{html.escape(row['whatsapp_url'])}' target='_blank'>WhatsApp</a>")
        if row.get("google_maps"):
            actions.append(f"<a class='button' href='{html.escape(row['google_maps'])}' target='_blank'>Maps</a>")
        if row.get("website"):
            actions.append(f"<a class='button' href='{html.escape(row['website'])}' target='_blank'>Site atual</a>")
        if row.get("url_detectada"):
            actions.append(f"<a class='button' href='{html.escape(row['url_detectada'])}' target='_blank'>Evidencia</a>")
        return f"""<tr>
  <td>{html.escape(str(row["rank"]))}</td>
  <td class="{html.escape(chance_class)}">{html.escape(row["chance"])}</td>
  <td class="score">{html.escape(str(row["score"]))}</td>
  <td><strong>{html.escape(row["nome"])}</strong><div class="small">{html.escape(row["categoria_original"])}</div></td>
  <td>{html.escape(row["cidade"])} / {html.escape(row["estado"])}</td>
  <td>{html.escape(row["presenca_digital"])}</td>
  <td class="small">{html.escape(row["motivo"])}</td>
  <td>{''.join(actions)}</td>
</tr>"""


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_input(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path
    csv_files = sorted(Path.cwd().glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not csv_files:
        raise FileNotFoundError("Nenhum CSV encontrado. Use --input caminho/do/arquivo.csv")
    return csv_files[0].resolve()


def normalize_for_match(value: str) -> str:
    value = strip_accents(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def analyze(
    input_path: Path,
    output_dir: Path,
    config_path: Path,
    enrich_web: bool = False,
    max_enrich: int = 30
) -> dict[str, Any]:
    config = load_config(config_path)
    rows, encoding = read_csv_rows(input_path)
    mapper = ColumnMapperAgent()
    mapping = mapper.detect_mapping(rows)
    presence_agent = PresenceAgent(config)
    enrichment_agent = WebEnrichmentAgent()
    niche_agent = NicheAgent(config)
    scoring_agent = ScoringAgent(config)
    message_agent = MessageAgent()
    exporter = ExportAgent()

    leads: list[Lead] = []
    for row in rows:
        lead = Lead(raw=row, mapped=mapper.map_row(row, mapping))
        presence_agent.classify(lead)
        if enrich_web and max_enrich > 0 and lead.presence_type in {"sem_site", "site_informado"}:
            enrichment_agent.enrich(lead)
            max_enrich -= 1
            time.sleep(0.15)
        niche_agent.classify(lead)
        scoring_agent.score(lead)
        message_agent.make(lead)
        leads.append(lead)

    return exporter.export(leads, output_dir, input_path, encoding)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisa CSVs de negocios locais e prioriza leads para venda de sites.")
    parser.add_argument("--input", "-i", help="Caminho do CSV. Se vazio, usa o CSV mais recente da pasta atual.")
    parser.add_argument("--output-dir", "-o", default=str(DEFAULT_OUTPUT_DIR), help="Pasta onde os arquivos serao gerados.")
    parser.add_argument("--config", "-c", default=str(DEFAULT_CONFIG), help="Arquivo de configuracao de nichos e pesos.")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON formatado no terminal.")
    parser.add_argument("--enrich-web", action="store_true", help="Pesquisa app/presenca externa quando o CSV nao traz site.")
    parser.add_argument("--max-enrich", type=int, default=30, help="Maximo de leads sem site que serao pesquisados online.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = resolve_input(args.input)
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    config_path = Path(args.config).expanduser()
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    manifest = analyze(input_path, output_dir, config_path, enrich_web=args.enrich_web, max_enrich=args.max_enrich)
    print(json.dumps(manifest, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
