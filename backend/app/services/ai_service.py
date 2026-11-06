from __future__ import annotations


def draft_sales_reply(lead: dict, incoming_message: str) -> str:
    name = lead.get("nome") or "sua empresa"
    text = (incoming_message or "").strip().lower()

    if any(word in text for word in ["preco", "preço", "valor", "quanto", "custa"]):
        return (
            f"Perfeito. Para a {name}, eu montaria algo enxuto e profissional primeiro: página inicial, "
            "serviços, fotos, avaliações, mapa e botão de WhatsApp. O valor depende do nível de acabamento, "
            "mas posso te mostrar uma prévia antes para você decidir com calma."
        )

    if any(word in text for word in ["sim", "pode", "manda", "quero", "mostrar"]):
        return (
            "Boa. Vou te mandar uma ideia simples de como ficaria a página, com foco em passar confiança "
            "para quem encontra vocês no Google e levar a pessoa direto para o WhatsApp."
        )

    if any(word in text for word in ["nao", "não", "agora", "depois"]):
        return (
            "Tranquilo, sem problema. Vou deixar a ideia separada aqui. Se fizer sentido mais pra frente, "
            "posso te mostrar um modelo rápido sem compromisso."
        )

    return (
        "Obrigado pelo retorno. A ideia é bem direta: criar uma presença profissional que concentre serviços, "
        "localização, avaliações e WhatsApp para transformar busca no Google em contato. Posso te mostrar uma prévia?"
    )
