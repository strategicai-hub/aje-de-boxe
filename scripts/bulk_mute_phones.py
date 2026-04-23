"""
Silencia em lote telefones lidos de um CSV.

Seta a chave `<phone>--aje:mute` no Redis com TTL fixo.
Enquanto a chave existir:
  - webhook rejeita a mensagem (nao publica no RabbitMQ)
  - consumer tambem ignora (defesa em profundidade)

Uso:
  python scripts/bulk_mute_phones.py <csv_path> [--hours 15]

O CSV precisa ter uma coluna `phone_number` (formato com ou sem `+`).
"""
import argparse
import csv
import sys
from pathlib import Path

# Ajusta sys.path pra permitir rodar direto da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import redis  # noqa: E402

from app.config import settings  # noqa: E402
from app.services import redis_keys as keys  # noqa: E402


def _normalize_phone(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("+"):
        raw = raw[1:]
    return "".join(ch for ch in raw if ch.isdigit())


def main() -> int:
    parser = argparse.ArgumentParser(description="Silencia em lote telefones de um CSV.")
    parser.add_argument("csv_path", help="Caminho do CSV com coluna phone_number")
    parser.add_argument("--hours", type=float, default=15, help="TTL em horas (padrao 15)")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"CSV nao encontrado: {csv_path}", file=sys.stderr)
        return 1

    ttl = int(args.hours * 3600)

    phones: list[str] = []
    seen: set[str] = set()
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "phone_number" not in (reader.fieldnames or []):
            print("CSV precisa ter coluna 'phone_number'", file=sys.stderr)
            return 1
        for row in reader:
            phone = _normalize_phone(row.get("phone_number", ""))
            if phone and phone not in seen:
                seen.add(phone)
                phones.append(phone)

    if not phones:
        print("Nenhum telefone valido encontrado no CSV.")
        return 0

    r = redis.from_url(settings.redis_url, decode_responses=True)
    pipe = r.pipeline()
    for phone in phones:
        pipe.set(keys.mute_key(phone), "1", ex=ttl)
    pipe.execute()

    print(f"Silenciados {len(phones)} numero(s) por {args.hours}h (TTL {ttl}s).")
    print(f"Exemplo de chave: {keys.mute_key(phones[0])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
