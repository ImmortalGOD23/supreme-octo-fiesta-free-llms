# Operação dos gateways

## FreeLLMAPI

Execute `python super-fcc.py up freellmapi`, abra http://127.0.0.1:3001 e conclua o onboarding. Adicione chaves em Keys, configure a cadeia e copie o token unificado. Use esse token em `models freellmapi` e `connect freellmapi ID`.

O volume `super-fcc_freellmapi-data` guarda dados. Faça backup desse volume junto com `.runtime/stack.env`, pois ele contém a chave de criptografia. Não regenere essa chave ao restaurar o banco.

## 9router

Execute `python super-fcc.py up 9router`, abra http://127.0.0.1:20128 e use a senha gerada em `.runtime/stack.env`. Cadastre contas/provedores no painel e copie a chave do endpoint. Use-a nos comandos `models 9router` e `connect 9router ID`. A integração não habilita Headroom, MITM ou sincronização cloud.

## CLIProxyAPI

O arquivo `.runtime/cliproxyapi.yaml` usa o layout v8 do commit fixado. Para configurar um upstream OpenAI-compatible, use os exemplos de `upstream/cliproxyapi/config.example.yaml`, preservando `access`, `management`, `server` e `oauth.auth-dir` locais. Reinicie com `python super-fcc.py stop cliproxyapi` e `python super-fcc.py up cliproxyapi`.

Para descobrir os comandos de autenticação oferecidos por essa versão:

```bash
docker compose --env-file .runtime/stack.env run --rm cliproxyapi ./CLIProxyAPI --help
```

Alguns fluxos OAuth exigem callbacks e portas adicionais. O Compose só publica 8317; antes de usar um login específico, siga a documentação do upstream para o fluxo headless e, se necessário, acrescente somente a porta correspondente com bind em localhost. Nenhuma conta é autenticada automaticamente.

A chave de cliente é lida automaticamente de `.runtime/cliproxyapi.key`. A chave administrativa está em `.runtime/cliproxyapi-management.key`. O gerenciamento remoto fica desativado. A montagem do YAML é somente leitura; gerenciamento que tenta gravar configuração deve ser feito no host, não pelo painel.

## Restauração FCC

Pare FCC. Os backups `~/.fcc/.env.super-fcc-*.bak` foram feitos imediatamente antes de cada gravação do helper. Copie o backup escolhido sobre `~/.fcc/.env` e reinicie FCC. A restauração substitui a configuração inteira; mantenha uma cópia da atual caso tenha alterações posteriores. O projeto não faz rollback automático nem apaga volumes.
