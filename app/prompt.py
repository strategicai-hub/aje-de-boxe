"""
Gera o SYSTEM_PROMPT a partir do template Jinja2 + dados do client.yaml.
"""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from app.client_data import load_client_data
from app.services import sai_sync

_SP_TZ = ZoneInfo("America/Sao_Paulo")


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _compute_closed_days_block(horizon_days: int = 90) -> str:
    """Bloco autoritativo de datas FECHADAS (feriados/recessos do painel SAI)."""
    snap = sai_sync.load_snapshot_sync()
    if not snap:
        return ""
    holidays = ((snap.get("assistant") or {}).get("holidays") or [])
    if not holidays:
        return ""
    today = datetime.now(_SP_TZ).date()
    horizon = today + timedelta(days=horizon_days)
    lines: list[str] = []
    for h in holidays:
        start = _parse_iso_date(h.get("startDate") or "")
        end = _parse_iso_date(h.get("endDate") or h.get("startDate") or "")
        if start is None or end is None:
            continue
        if end < today or start > horizon:
            continue
        reason = (h.get("reason") or "").strip()
        if start == end:
            label = start.strftime("%d/%m/%Y")
        else:
            label = f"{start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}"
        lines.append(f"  - {label}" + (f" — {reason}" if reason else ""))
    if not lines:
        return ""
    return (
        "\n\n## DATAS FECHADAS - REGRA ABSOLUTA\n"
        "Nas datas listadas abaixo a unidade **NAO abre** (feriado/recesso "
        "cadastrado no painel). PROIBIDO oferecer ou confirmar agendamento de "
        "aula experimental/avaliacao nessas datas — mesmo que a tabela de "
        "horarios normalmente tenha atividade naquele dia da semana. Se o lead "
        "perguntar se vai abrir, responda que estaremos fechados, cite o motivo "
        "se houver, e ofereca o proximo dia util compativel.\n\n"
        + "\n".join(lines)
        + "\n"
    )


def _compute_time_context_block() -> str:
    """Bloco autoritativo de data/hora atual em Sao Paulo.

    Injetado no FINAL do prompt (modelos seguem melhor instrucoes no final).
    Inclui hoje + ontem + amanha ja computados para evitar erros de calculo.
    """
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
    return (
        template.render(**data)
        + _compute_time_context_block()
        + _compute_closed_days_block()
    )


def get_system_prompt() -> str:
    """Renderiza o prompt sob demanda (contexto temporal reflete o agora)."""
    return build_prompt()
