from __future__ import annotations


def generate_sales_message(lead: dict) -> str:
    name = lead.get("nome") or "sua empresa"
    category = lead.get("categoria_original") or lead.get("nicho") or "serviço"
    city = lead.get("cidade") or "sua região"
    presence = (lead.get("presenca_digital") or "").lower()

    if "site proprio" in presence or "tem site" in presence:
        return (
            f"Fala {name}, tudo bem?\n\n"
            "Dei uma olhada na presença online de vocês e vi alguns pontos que dariam pra melhorar "
            "na parte de apresentação, confiança e conversão.\n\n"
            "Montei uma ideia de site mais direto para transformar visitas em contatos pelo WhatsApp, "
            "sem perder o que vocês já têm hoje.\n\n"
            "Posso te mostrar sem compromisso?"
        )

    if "rede social" in presence or "instagram" in presence:
        return (
            f"Fala {name}, tudo bem?\n\n"
            f"Vi que vocês usam rede social como principal presença online em {city}. Isso ajuda bastante, "
            "mas muita gente que vem pelo Google procura uma página mais organizada com serviços, localização, "
            "avaliações e botão direto de WhatsApp.\n\n"
            "Montei um modelo de site baseado no negócio de vocês para centralizar tudo e passar mais confiança.\n\n"
            "Quer ver como ficaria?"
        )

    if "app android" in presence or "app" in presence:
        return (
            f"Fala {name}, tudo bem?\n\n"
            "Vi que vocês já têm app, isso é um ótimo sinal de maturidade digital. O que normalmente falta nesses casos "
            "é um site central, com domínio próprio, para apresentar melhor o negócio no Google e levar o cliente para "
            "o app, WhatsApp ou agendamento.\n\n"
            "Montei uma ideia de página profissional para funcionar como vitrine e ponte de conversão.\n\n"
            "Posso te mostrar?"
        )

    if "agendamento" in presence:
        return (
            f"Fala {name}, tudo bem?\n\n"
            "Vi que vocês usam uma plataforma de agendamento. Isso resolve a agenda, mas nem sempre vende bem o negócio "
            "para quem ainda está escolhendo onde comprar.\n\n"
            "A ideia seria ter um site próprio com apresentação, fotos, avaliações, localização e botão levando para o "
            "agendamento atual.\n\n"
            "Quer ver um modelo simples?"
        )

    return (
        f"Fala {name}, tudo bem?\n\n"
        f"Estava procurando {category} em {city} e vi que vocês ainda não parecem ter um site próprio bem centralizado.\n\n"
        "Hoje muita gente decide pelo Google, então uma página com serviços, avaliações, localização e WhatsApp pode "
        "ajudar a transformar busca em contato.\n\n"
        "Montei um modelo baseado no negócio de vocês para mostrar como ficaria.\n\n"
        "Quer ver sem compromisso?"
    )

