from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


@dataclass
class CollectedLead:
    nome: str
    categoria: str
    cidade: str
    telefone: str = ""
    website: str = ""
    instagram: str = ""
    endereco: str = ""
    estado: str = ""
    origem: str = ""
    origem_id: str = ""
    google_maps: str = ""
    nota: str = ""
    avaliacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class LeadProvider(ABC):
    name: str

    @abstractmethod
    def search(self, niche: str, city: str, limit: int) -> list[CollectedLead]:
        """Return raw leads from this source."""
