from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.collectors.base import CollectedLead, LeadProvider


class GooglePlacesProvider(LeadProvider):
    name = "google_places"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY", "")

    def search(self, niche: str, city: str, limit: int) -> list[CollectedLead]:
        if not self.api_key:
            raise RuntimeError("Configure GOOGLE_PLACES_API_KEY para usar o provider google_places.")

        query = f"{niche} em {city}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json?" + urlencode(
            {"query": query, "key": self.api_key, "language": "pt-BR"}
        )
        payload = self._get_json(url)
        results = payload.get("results", [])[: max(1, min(int(limit or 10), 60))]

        leads: list[CollectedLead] = []
        for item in results:
            details = self._details(item.get("place_id", ""))
            leads.append(
                CollectedLead(
                    nome=details.get("name") or item.get("name", ""),
                    categoria=niche,
                    cidade=city,
                    telefone=details.get("formatted_phone_number", ""),
                    website=details.get("website", ""),
                    endereco=details.get("formatted_address") or item.get("formatted_address", ""),
                    origem=self.name,
                    origem_id=item.get("place_id", ""),
                    google_maps=details.get("url", ""),
                    nota=str(item.get("rating", "")),
                    avaliacoes=str(item.get("user_ratings_total", "")),
                )
            )
        return leads

    def _details(self, place_id: str) -> dict:
        if not place_id:
            return {}
        fields = "name,formatted_phone_number,website,formatted_address,url"
        url = "https://maps.googleapis.com/maps/api/place/details/json?" + urlencode(
            {"place_id": place_id, "fields": fields, "key": self.api_key, "language": "pt-BR"}
        )
        return self._get_json(url).get("result", {})

    def _get_json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": "Lobo-Walstreet/1.0"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
