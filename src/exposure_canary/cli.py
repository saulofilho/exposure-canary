"""CLI for exposure-canary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .errors import Error
from .events import load_webhook_file
from .service import create_canary, import_webhook, render_report
from .state import State
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exposure-canary",
        description="Iscas defensivas para ativos que você controla.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"exposure-canary {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Cria uma isca em um ativo seu")
    create.add_argument("--kind", required=True, choices=("url", "dns", "email"))
    create.add_argument("--label", required=True, help="Superfície em que a isca será plantada")
    create.add_argument("--asset", required=True, help="Ativo que você controla")
    create.add_argument("--owned", action="store_true", help="Confirma que o ativo é seu")
    create.add_argument("--collector", help="Base https do coletor, para kind=url")
    create.add_argument("--zone", help="Zona DNS que você administra, para kind=dns")
    create.add_argument("--domain", help="Domínio de e-mail que você recebe, para kind=email")
    create.add_argument("--state", default=".exposure-canary", help="Diretório do registro")

    ingest = commands.add_parser("import-webhook", help="Importa um JSON de webhook")
    ingest.add_argument("webhook", help="Arquivo JSON, ou - para stdin")
    ingest.add_argument("--state", default=".exposure-canary", help="Diretório do registro")

    report = commands.add_parser("report", help="Gera o relatório Markdown")
    report.add_argument("--state", default=".exposure-canary", help="Diretório do registro")
    report.add_argument("-o", "--output", help="Arquivo de saída")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            return _create(args)
        if args.command == "import-webhook":
            return _import(args)
        return _report(args)
    except Error as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


def _create(args: argparse.Namespace) -> int:
    state = State.load(args.state)
    canary = create_canary(
        state,
        kind=args.kind,
        label=args.label,
        asset=args.asset,
        owned=args.owned,
        collector=args.collector,
        zone=args.zone,
        domain=args.domain,
    )
    print(json.dumps(canary.to_dict(), ensure_ascii=False))
    print(f"Isca criada em {state.path}", file=sys.stderr)
    return 0


def _import(args: argparse.Namespace) -> int:
    state = State.load(args.state)
    result = import_webhook(state, load_webhook_file(args.webhook))
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


def _report(args: argparse.Namespace) -> int:
    state = State.load(args.state)
    report = render_report(state)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")
        print(f"Relatório gerado em {destination}", file=sys.stderr)
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
