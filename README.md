# Exposure Canary

Iscas defensivas para ativos que você controla. A v1 cria o token, importa o JSON do seu coletor, deduplica, classifica a severidade e gera um relatório Markdown.

Três tipos:

- **URL** — `https://<coletor>/c/<id>`
- **DNS** — `<id>.<zona>`
- **E-mail** — `cn-<hex>@<domínio>`

A ferramenta não identifica pessoa nem intenção. Também não cobre pesquisa feita fora da isca. O `state.json` guarda os ids: deixe o diretório fora do git.

## Instalação

```bash
pip install -e ".[mcp]"
```

Sem o extra `mcp`, a CLI e a biblioteca funcionam. O servidor MCP precisa do extra.

## CLI

```bash
exposure-canary create \
  --kind url --label pagina --asset site \
  --collector https://collect.example --owned

exposure-canary create \
  --kind dns --label zona --asset example.com \
  --zone example.com --owned

exposure-canary create \
  --kind email --label contato --asset example.com \
  --domain example.com --owned

exposure-canary import-webhook webhook.json
exposure-canary report -o relatorio.md
```

`--owned` confirma que o ativo é seu. O registro fica em `.exposure-canary/` salvo `--state`.

Webhook de exemplo:

```json
{
  "canary_id": "cn0123456789abcdef",
  "observed_at": "2026-10-14T12:00:00Z",
  "source": "203.0.113.10"
}
```

Também vale uma lista, ou `{"events": [...]}`. O id pode vir dentro de `url`, `path`, `address` ou `qname`. Duplicata é a mesma isca, a mesma origem e a mesma janela de 5 minutos.

## Biblioteca

```python
from exposure_canary import State, create_canary, import_webhook, render_report

state = State.load(".exposure-canary")
canary = create_canary(
    state,
    kind="dns",
    label="zona",
    asset="example.com",
    owned=True,
    zone="example.com",
)
import_webhook(state, {"qname": canary.value, "observed_at": "2026-10-14T12:00:00Z", "source": "203.0.113.10"})
print(render_report(State.load(".exposure-canary")))
```

`import_webhook` já grava o estado. A chamada seguinte recarrega o arquivo.

## MCP

Tools: `create_canary`, `import_webhook`, `render_report`.

Entrypoint: `exposure-canary-mcp`.

`.cursor/mcp.json` sobe o servidor com `uv run --extra mcp`, a partir da raiz deste repositório. O `uv` precisa estar no PATH.

## Skill

Um texto só, em dois caminhos que o teste `test_skill` exige iguais:

- `plugin/skills/exposure-canary/SKILL.md` — plugin Claude
- `.cursor/skills/exposure-canary/SKILL.md` — Cursor

A skill limita o uso a ativos próprios, diz onde plantar, como ler o alerta e onde parar.

## Severidade

| Evento | Severidade |
| --- | --- |
| DNS ou e-mail, observação nova | Alta |
| URL, primeira origem | Média |
| URL, origem diferente da primeira | Alta |
| URL, mesma origem fora da janela | Baixa |
| Token que não está no registro | Baixa |
| Mesma isca, origem e janela de 5 minutos | ignorada |
