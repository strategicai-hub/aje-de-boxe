"""
Gera o SYSTEM_PROMPT a partir do template Jinja2 + dados do client.yaml.
"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from app.client_data import load_client_data

_SP_TZ = ZoneInfo("America/Sao_Paulo")


def _compute_time_context_block() -> str:
    """Bloco autoritativo de data/hora atual em Sao Paulo.

    Injetado no FINAL do prompt (modelos seguem melhor instrucoes no final).
    Inclui hoje + ontem + amanha ja computados para evitar erros de calculo.
    """
    from datetime import timedelta
    week = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo",
    ]
    now = datetime.now(_SP_TZ)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    return (
        "\n\n---\n\n## DATA E HORA ATUAIS - REGRA ABSOLUTA\n"
        "Estas informações são AUTORITATIVAS. Substituem qualquer suposição sua. "
        "Use-as sempre que for falar de dia, data, hoje, ontem, amanhã, semana ou horário:\n\n"
        f"- AGORA (America/Sao_Paulo): {now.strftime('%d/%m/%Y %H:%M')}\n"
        f"- HOJE é {week[now.weekday()]} ({now.strftime('%d/%m/%Y')}).\n"
        f"- ONTEM foi {week[yesterday.weekday()]} ({yesterday.strftime('%d/%m/%Y')}).\n"
        f"- AMANHÃ será {week[tomorrow.weekday()]} ({tomorrow.strftime('%d/%m/%Y')}).\n\n"
        "PROIBIDO inventar outro dia da semana. Se for mencionar \"amanhã\", "
        f"obrigatoriamente é {week[tomorrow.weekday()]}.\n"
    )


def build_prompt() -> str:
    template_dir = Path(__file__).parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("prompt_template.j2")
    data = load_client_data()
    return template.render(**data) + _compute_time_context_block()


def get_system_prompt() -> str:
    """Renderiza o prompt sob demanda (contexto temporal reflete o agora)."""
    return build_prompt()
