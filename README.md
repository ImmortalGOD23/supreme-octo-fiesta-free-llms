# Supreme Octo Fiesta Free LLMs

**Super FCC** — integração pessoal com Free Claude Code como núcleo.

Estação pessoal de IA com **Free Claude Code como núcleo**, NVIDIA NIM nativa e três gateways opcionais. Inclui todos os cinco repositórios enviados, como submódulos fixados em commits e com suas licenças preservadas.

| Componente | Papel |
| --- | --- |
| `upstream/fcc` | Servidor principal, Admin, agentes e roteamento |
| `upstream/cliproxyapi` | Gateway de contas OAuth e APIs |
| `upstream/9router` | Dashboard, combos e provedores |
| `upstream/freellmapi` | Agregação de APIs gratuitas e fallback |
| `upstream/free-llm` | Catálogo local de referência e exemplos |
| NVIDIA NIM | Provedor nativo do FCC; não é um repositório adicional |

O projeto integra os sistemas sem fundir seus bancos ou reimplementar seus adaptadores. O FCC conversa diretamente com a NVIDIA ou com **um** gateway escolhido. A configuração de contas dentro de cada gateway continua em seu painel.

## Estado da entrega

Orquestrador, configuração Docker, integração com o schema real do FCC, testes locais e fontes fixadas. **O servidor Python FCC foi instalado com sucesso.** O launcher usa uv `0.13.7` isolado e instala Python `3.14.10`, sem substituir o uv do sistema. As compilações dos gateways e a inferência real ainda precisam ser validadas na máquina de uso. Veja [validação](docs/VALIDACAO.md).

## Começar

Requisitos: Git, Python 3.11+ para o orquestrador, uv (o launcher obtém a versão compatível) e Docker Compose para os gateways opcionais. Os comandos Python funcionam no Windows usando `python` e no Linux/macOS usando `python3`. Os serviços Docker aqui são Linux; Docker Desktop atende Windows/macOS.

```bash
git clone --recurse-submodules https://github.com/ImmortalGOD23/supreme-octo-fiesta-free-llms.git super-fcc
cd super-fcc
python super-fcc.py init
python super-fcc.py doctor
python super-fcc.py install-fcc
```

Se recebeu uma cópia Git sem os fontes: `git submodule update --init --recursive`. Repositório: https://github.com/ImmortalGOD23/supreme-octo-fiesta-free-llms.

### NVIDIA como principal

Pare seu servidor FCC antes de aplicar mudanças. A configuração usa o **mesmo `~/.fcc/.env` do FCC instalado**, com backup privado antes de cada alteração; não a execute em paralelo com o painel Admin.

```bash
python super-fcc.py models nvidia
python super-fcc.py configure-nvidia
python super-fcc.py serve
```

A chave é solicitada em entrada oculta; também pode vir da variável `NVIDIA_API_KEY`. Não coloque chaves no Git. O comando consulta `/models` antes de aplicar o perfil que você mostrou nas capturas:

1. Principal: `nvidia/nemotron-3-ultra-550b-a55b`
2. Fallback: `minimaxai/minimax-m3.1-flash`
3. Fallback: `z-ai/glm-5.3-flash`

Se algum ID não existir mais, a alteração é interrompida. A consulta de catálogo não comprova que a inferência estará autorizada ou disponível. O comando preserva chaves anteriores, coloca a informada em Key 1 e substitui o perfil de modelos/fallback, removendo overrides de tiers para usar o principal em todos eles. Se já está satisfeito com sua configuração NVIDIA, **pule configure-nvidia**.

Em outro terminal, na pasta de código em que deseja trabalhar, use o launcher do FCC instalado (`fcc-claude`). Alternativamente, `python /caminho/super-fcc/super-fcc.py agent claude` inicia o agente na sua pasta atual. O agente precisa estar instalado conforme as instruções do FCC; este projeto instala o servidor Python, não o Claude Code/Codex em si.

### Gateways opcionais

```bash
python super-fcc.py up freellmapi
# ou
python super-fcc.py up 9router
python super-fcc.py up cliproxyapi
```

Os serviços são construídos dos commits fixados, em vez de imagens `latest`. A primeira compilação pode demorar e exige versões de imagens e pacotes disponíveis para os upstreams.

| Serviço | Painel/API | Primeiro acesso |
| --- | --- | --- |
| FCC | URL exibida por `serve` (porta padrão 8082) | Autenticação conforme FCC |
| FreeLLMAPI | http://127.0.0.1:3001 | Crie a conta local, cadastre suas chaves e copie a chave unificada |
| 9router | http://127.0.0.1:20128 | Senha `NINEROUTER_PASSWORD` no arquivo privado `.runtime/stack.env` |
| CLIProxyAPI | http://127.0.0.1:8317/v1 | Configure provedores no YAML local ou login pelo CLI |

O CLIProxyAPI tem gerenciamento remoto desativado: use seu CLI dentro do contêiner ou edite `.runtime/cliproxyapi.yaml` e reinicie o serviço. O painel administrativo baixado pelo upstream não é disponibilizado remotamente por este projeto. [Detalhes dos gateways](docs/GATEWAYS.md).

Depois de configurar um provedor **dentro do gateway**, consulte e conecte um modelo real ao FCC:

```bash
python super-fcc.py models freellmapi
python super-fcc.py connect freellmapi ID-EXATO-RETORNADO --use-as fallback
```

Troque `freellmapi` por `9router` ou `cliproxyapi` conforme o serviço. `connect` verifica o ID via `/models`, registra um provedor personalizado usando Chat Completions e pode disponibilizá-lo (`available`, padrão), torná-lo principal (`default`) ou acrescentá-lo como reserva (`fallback`). Reinicie FCC e abra uma nova sessão após aplicar. Com `default`, overrides existentes de tiers continuam ativos; revise-os no Admin.

O identificador `auto` do FreeLLMAPI pode ser virtual e nem sempre aparece em `/models`; escolha um ID listado. Para recursos específicos de Responses/Messages, configure outro formato pelo Admin FCC; o adaptador deste repositório usa `openai_chat`.

```bash
python super-fcc.py logs freellmapi
python super-fcc.py stop freellmapi
python super-fcc.py catalog
```

Os volumes persistem ao parar serviços. Não é necessário executar os três gateways simultaneamente. O Free-LLM é documentação consultável em `upstream/free-llm/README.md`, não um serviço de inferência.

## Privacidade, custos e limites

As portas dos gateways são publicadas somente em localhost. O FCC é configurado para localhost quando o perfil NVIDIA é aplicado. Uma instalação FCC já existente mantém suas configurações se você pular esse passo. Chaves geradas ficam em `.runtime/`, ignoradas pelo Git; as cadastradas no FCC permanecem no armazenamento próprio dele. Backups FCC também contêm segredos: guarde-os como o arquivo original.

O FreeLLMAPI tem catálogo gratuito defasado em 30 dias em relação ao premium. Cada provedor controla suas próprias cotas e termos. Fallback entre gateways pode reenviar seu contexto para outro provedor e consumir mais de uma cota. Recursos como cloud sync do 9router e compression/fusion não são ativados automaticamente. RTK/Headroom podem ser configurados pelos projetos originais, mas não são dependências adicionadas desta integração.

## Desenvolvimento e licença

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Veja [arquitetura](docs/ARQUITETURA.md), [validação](docs/VALIDACAO.md) e [atribuições](THIRD_PARTY.md). O código de integração usa AGPL-3.0-only; cada submódulo mantém sua licença. Os commits em `upstreams.lock.json` correspondem aos gitlinks. Atualizações de upstream devem atualizar ambos e passar pelos testes de contrato.
