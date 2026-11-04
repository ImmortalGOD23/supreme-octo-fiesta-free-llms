# Validação da entrega

## Executado neste ambiente

- Clonagem dos cinco projetos; commits registrados em `upstreams.lock.json` e gitlinks.
- Inicialização idempotente de configurações privadas e teste de permissões 0600.
- Docker Compose validado com `config --quiet`; daemon Docker 28.4.0 acessível.
- Atualização isolada de uv 0.12.23 para execução via uv 0.13.7. A versão nova reconhece e instala Python 3.14.10, exigido pelo FCC.
- Instalação completa do pacote FCC fixado e suas dependências: concluída.
- Seis testes do orquestrador e três testes de contrato com o armazenamento/schema real do FCC: passaram.
- Testes de contrato usam um diretório temporário via patch de Path.home; não alteram a configuração FCC real.
- Sem chaves NVIDIA ou de outros provedores no ambiente. Não houve inferência paga ou gratuita.

## Limites do que foi validado

Os três gateways não foram compilados nem iniciados nesta entrega. Foram integrados por build contexts dos fontes, portas locais, armazenamento persistente e conexão via `/models` + Chat Completions ao FCC. A sintaxe Compose foi validada, mas isso não comprova builds, login OAuth ou chamadas reais. Nenhum agente Claude Code/Codex foi instalado pelo projeto. Nenhum desempenho ou economia de tokens foi medido.

## Repetir os testes

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python super-fcc.py install-fcc
PYTHONPATH=src:upstream/fcc/src upstream/fcc/.venv/bin/python -m unittest discover -s tests -v
python super-fcc.py init
docker compose --env-file .runtime/stack.env config --quiet
```

No Windows, defina PYTHONPATH com `;` e use `upstream/fcc/.venv/Scripts/python.exe`. Não use a sintaxe Unix de variável inline no PowerShell.

## GitHub

Repositório: https://github.com/ImmortalGOD23/supreme-octo-fiesta-free-llms.

A autenticação do CLI gh deste ambiente está inválida, mas a conexão GitHub do Codex tem permissão de escrita e permite publicar via API Git. O commit inicial criado pelo usuário é preservado como ancestral.
