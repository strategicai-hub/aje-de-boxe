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
    """Bloco fixo no topo do prompt informando data/hora atual em São Paulo.

    Sem isso o modelo chuta o dia da semana e erra (ex.: dizia "sexta" num domingo).
    """
    now = datetime.now(_SP_TZ)
    weekday_full = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo",
    ][now.weekday()]
    data_str = now.strftime("%d/%m/%Y")
    hora_str = now.strftime("%H:%M")
    return (
        "## CONTEXTO TEMPORAL (autoritativo)\n"
        f"- Hoje é {weekday_full}, {data_str}.\n"
        f"- Hora atual em São Paulo: {hora_str}.\n"
        "- Use SEMPRE estas informações ao mencionar dia, data ou hora. "
        "Nunca invente outro dia da semana.\n"
    )


def build_prompt() -> str:
    template_dir = Path(__file__).parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("prompt_template.j2")
    data = load_client_data()
    return _compute_time_context_block() + "\n" + template.render(**data)


def get_system_prompt() -> str:
    """Renderiza o prompt sob demanda (contexto temporal reflete o agora)."""
    return build_prompt()
