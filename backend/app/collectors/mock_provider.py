from __future__ import annotations

import hashlib

from backend.app.collectors.base import CollectedLead, LeadProvider


class MockLeadProvider(LeadProvider):
    name = "mock"

    def search(self, niche: str, city: str, limit: int) -> list[CollectedLead]:
        limit = max(1, min(int(limit or 10), 100))
        normalized_niche = niche.strip().title() or "Negocio Local"
        normalized_city = city.strip().title() or "Cidade"
        names = [
            "Prime",
            "Central",
            "Nova",
            "Studio",
            "Classe A",
            "Ponto Certo",
            "Elite",
            "Nobre",
            "Mais",
            "Pro",
            "Real",
            "Villa",
        ]
        streets = [
            "Rua das Palmeiras",
            "Avenida Brasil",
            "Rua Sao Pedro",
            "Avenida Central",
            "Rua XV de Novembro",
            "Rua da Praia",
        ]

        leads: list[CollectedLead] = []
        for index in range(limit):
            seed = hashlib.sha1(f"{normalized_niche}|{normalized_city}|{index}".encode("utf-8")).hexdigest()
            name = f"{normalized_niche} {names[index % len(names)]}"
            phone = f"+55 48 9{int(seed[:7], 16) % 9000 + 1000:04d}-{int(seed[7:11], 16) % 9000 + 1000:04d}"
            has_site = index % 4 == 0
            instagram_only = index % 4 == 1
            website = f"https://www.{self._slug(name)}.com.br" if has_site else ""
            instagram = f"https://instagram.com/{self._slug(name)}" if instagram_only else ""
            address = f"{streets[index % len(streets)]}, {100 + index * 7}"
            origem_id = f"mock-{self._slug(normalized_city)}-{self._slug(normalized_niche)}-{index}"
            leads.append(
                CollectedLead(
                    nome=name,
                    categoria=normalized_niche,
                    cidade=normalized_city,
                    estado="Santa Catarina",
                    telefone=phone,
                    website=website or instagram,
                    instagram=instagram,
                    endereco=address,
                    origem=self.name,
                    origem_id=origem_id,
                    google_maps=f"https://www.google.com/maps/search/?api=1&query={self._slug(name)}",
                    nota=str(round(4.1 + (index % 9) / 10, 1)),
                    avaliacoes=str(18 + index * 13),
                )
            )
        return leads

    def _slug(self, value: str) -> str:
        return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-").replace("--", "-")
