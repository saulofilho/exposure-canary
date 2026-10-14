---
name: exposure-canary
description: >-
  Cria iscas defensivas de URL, DNS e parte local de e-mail em ativos próprios,
  importa webhooks, deduplica eventos, classifica severidade e gera relatório
  Markdown pela CLI ou pelas tools MCP create_canary, import_webhook e
  render_report. Use quando o pedido for canary, isca, alerta de exposição,
  webhook de canário ou saber se alguém tocou um ativo seu. Pare em pedido de
  rastrear terceiros, fingerprint, pixel, identificar quem investigou ou
  desinformação.
---

# Exposure Canary

Use a biblioteca. Não escreva servidor, pixel ou coletor de fingerprint.

`state_path` absoluto, dentro do projeto do usuário. Default da CLI: `.exposure-canary`. O `state.json` fica fora do git.

## Escopo

Antes de criar uma isca, confirme qual ativo é do usuário: página, zona DNS ou domínio de e-mail que ele controla.

`owned` / `--owned` é a confirmação dele. Sem essa confirmação, não chame `create_canary`.

Uma isca por superfície. O `label` diz qual superfície foi tocada.

## Mapa de onde plantar

- **URL** — `value` no formato `https://<coletor>/c/<id>`, numa página ou arquivo que ele publica. O coletor é um host https dele. A v1 não inclui esse host: ele só exporta JSON.
- **DNS** — `value` no formato `<id>.<zona>`, na zona que ele administra. Coloque esse nome só no material que ele quer observar.
- **E-mail** — `value` no formato `cn-<hex>@<domínio>`, num único lugar. O domínio precisa receber correio dele.

Depois de `create_canary`, devolva `value` e diga onde plantar.

## Leitura do alerta

1. Peça o JSON que o coletor dele gravou. Campos aceitos: `canary_id` (ou o `value` da isca no texto), `observed_at`, `source`.
2. Chame `import_webhook`.
3. Chame `render_report` e explique a severidade:
   - **Alta** em DNS ou e-mail: aquela isca foi usada.
   - **Média** em URL: primeira origem a tocar essa URL.
   - **Alta** em URL: uma origem nova, diferente da primeira.
   - **Baixa**: a mesma origem voltou fora da janela de 5 minutos, ou o token não está no registro.
   - Duplicata na mesma janela, mesma origem e mesma isca: a importação ignora.
4. Diga o ativo e o rótulo. Pessoa, intenção e pesquisa feita fora da isca ficam de fora do relatório.

## Parada

Pare, sem código e sem isca, quando o pedido pedir:

- ativo de outra pessoa
- descobrir quem acessou, além da origem que o coletor dele já registrou
- fingerprint, pixel, user-agent, geolocalização ou dispositivo
- documento-isca, chave falsa, desinformação ou resposta à origem
- servidor para capturar visitantes

Nesse caso, diga que a v1 cobre criação da isca, importação do webhook e o relatório.

## Tools

- `create_canary(kind, label, asset, owned, state_path, collector|zone|domain)`
- `import_webhook(state_path, webhook_path ou payload_json)`
- `render_report(state_path, output_path opcional)`

CLI: `exposure-canary create`, `exposure-canary import-webhook`, `exposure-canary report`.
