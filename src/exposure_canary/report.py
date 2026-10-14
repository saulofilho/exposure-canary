"""Markdown report for owned-asset canaries."""

from __future__ import annotations

from datetime import datetime, timezone

from .state import State

_SEVERITY_PT = {"high": "Alta", "medium": "Média", "low": "Baixa"}
_KIND_PT = {"url": "URL", "dns": "DNS", "email": "E-mail", "unknown": "Desconhecido"}
_SEVERITY_ORDER = ("high", "medium", "low")


def render_report(state: State, *, generated_at: datetime | None = None) -> str:
    """Render the current state as Markdown."""
    moment = generated_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    stamp = moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Relatório de iscas",
        "",
        f"Gerado em {stamp}.",
        "",
        "O relatório registra horário, tipo da isca, ativo e a origem informada pelo seu coletor.",
        "Pessoa, intenção e buscas feitas fora da isca ficam de fora.",
        "",
        "## Resumo",
        "",
        "| Severidade | Eventos |",
        "| --- | --- |",
    ]
    counts = {name: 0 for name in _SEVERITY_ORDER}
    for event in state.events:
        if event.severity in counts:
            counts[event.severity] += 1
    for name in _SEVERITY_ORDER:
        lines.append(f"| {_SEVERITY_PT[name]} | {counts[name]} |")

    if state.last_import:
        last = state.last_import
        lines.extend(
            [
                "",
                (
                    "Última importação: "
                    f"{last.get('imported', 0)} novos, "
                    f"{last.get('duplicates', 0)} duplicados, "
                    f"{last.get('unmatched', 0)} sem registro."
                ),
            ]
        )

    lines.extend(["", "## Iscas", ""])
    if not state.canaries:
        lines.append("Nenhuma isca no registro.")
    else:
        lines.extend(
            [
                "| ID | Tipo | Rótulo | Ativo | Valor |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for canary in state.canaries:
            lines.append(
                f"| `{canary.id}` | {_KIND_PT.get(canary.kind, canary.kind)} | "
                f"{_cell(canary.label)} | {_cell(canary.asset)} | `{canary.value}` |"
            )

    lines.extend(["", "## Eventos", ""])
    if not state.events:
        lines.append("Nenhum evento.")
    else:
        known = state.canary_map()
        for name in _SEVERITY_ORDER:
            group = [event for event in state.events if event.severity == name]
            if not group:
                continue
            lines.extend([f"### {_SEVERITY_PT[name]}", ""])
            for event in group:
                canary = known.get(event.canary_id)
                label = canary.label if canary else "—"
                asset = canary.asset if canary else "—"
                lines.append(
                    f"- {event.observed_at} · {_KIND_PT.get(event.kind, event.kind)} · "
                    f"{_cell(label)} · ativo {_cell(asset)} · origem `{event.source}`"
                )
            lines.append("")

    if lines[-1] != "":
        lines.append("")
    lines.extend(
        [
            "## Leitura",
            "",
            "- Alta em DNS ou e-mail: aquela isca foi usada.",
            "- Média em URL: primeira origem a tocar essa URL.",
            "- Alta em URL: uma origem nova, diferente da primeira.",
            "- Baixa: a mesma origem voltou fora da janela de 5 minutos, ou o token não está no registro.",
            "- Duplicata na mesma janela, mesma origem e mesma isca: a importação ignora.",
            "- Guarde o JSON do webhook. Mantenha o `state.json` fora do git.",
            "",
        ]
    )
    return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
