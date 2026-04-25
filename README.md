# LPII AutoGrader

Sistema web de submissão, correção automática e publicação de notas para a disciplina **Linguagem de Programação II (LPII) — Programação Concorrente em C/C++**, ministrada pelo Prof. Bidu (Carlos Eduardo C. F. Batista) na UFPB.

## Visão Geral

O LPII AutoGrader permite ao professor definir trabalhos práticos de programação concorrente, aos alunos submeterem suas soluções (upload de ZIP ou link de repositório GitHub), e ao sistema compilar, testar e gerar feedback automaticamente — incluindo análise qualitativa via LLM local (Ollama).

### Funcionalidades

- **Submissão de código** via upload de ZIP ou link de repositório GitHub
- **Correção automática**: compilação (gcc), testes funcionais, stress testing, análise Helgrind
- **Análise qualitativa** via LLM local (Ollama com Qwen2.5-Coder)
- **Painel do professor**: criar trabalhos (com UI visual para configurar testes), gerenciar alunos, revisar submissões, ajustar notas, publicar, exportar CSV
- **CRUD de alunos**: cadastrar, editar, desativar/reativar alunos manualmente
- **Painel do aluno**: ver trabalhos com tempo restante, submeter, acompanhar status em tempo real, consultar notas e feedback
- **Sandbox de execução**: isolamento com `unshare`+`ulimit` (Linux) ou timeout básico (macOS/dev)
- **Estatísticas**: média, mediana, distribuição de notas por trabalho
- **Fila persistente**: crash recovery automático — submissões presas são re-enfileiradas
- **Safeguards**: rate limiting, whitelist de extensões, proteção contra zip bomb, validação de repo GitHub
- **Flash messages**: confirmação visual de todas as ações (submissão, publicação, edição)

### Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.9+ / FastAPI |
| Frontend | Jinja2 + HTMX + Tailwind CSS (CDN) |
| Banco de Dados | SQLite (via SQLAlchemy) |
| Worker | Processo Python separado com polling + crash recovery |
| Sandbox | `unshare` + `ulimit` (Linux) / `timeout` (macOS) |
| LLM | Ollama (remoto ou local) |
| Deploy | Gunicorn + Nginx + systemd |

---

## Estrutura do Projeto

```
lpii-autograder/
├── main.py                        # Entry point FastAPI + FlashMiddleware
├── config.py                      # Configuração centralizada
├── requirements.txt
├── alembic.ini
│
├── app/
│   ├── database.py                # Engine SQLAlchemy + session
│   ├── models.py                  # ORM: User, Assignment, Submission, GradeResult
│   ├── auth.py                    # Dependências de autenticação (cookie-based)
│   ├── security.py                # Hash bcrypt, sessões itsdangerous
│   ├── flash.py                   # Flash messages via cookie
│   ├── templating.py              # Jinja2 compartilhado + helper render() + filtros
│   ├── routers/
│   │   ├── auth_routes.py         # /login, /register, /logout
│   │   ├── student_routes.py      # /dashboard, /assignments, /submit, /grades
│   │   ├── professor_routes.py    # /admin/* (trabalhos, alunos, revisão, notas, config)
│   │   └── api_routes.py          # JSON API para HTMX polling
│   ├── services/
│   │   ├── submission_service.py  # Upload, validação, rate limiting, enfileiramento
│   │   ├── grader_service.py      # Pipeline completo de correção
│   │   ├── sandbox.py             # Execução isolada (unshare/timeout)
│   │   ├── llm_service.py         # Integração Ollama
│   │   └── github_service.py      # Clone de repos, checkout por deadline
│   └── utils/
│       └── file_utils.py          # Extração segura de ZIP (whitelist, zip bomb, path traversal)
│
├── grader/
│   ├── worker.py                  # Worker com polling + crash recovery
│   ├── compiler.py                # Wrapper gcc
│   ├── test_runner.py             # Testes funcionais
│   ├── stress_tester.py           # Stress testing (N execuções)
│   ├── helgrind_checker.py        # Valgrind --tool=helgrind
│   ├── structure_validator.py     # Validação de arquivos
│   └── report_generator.py        # Cálculo de nota
│
├── templates/                     # Jinja2 (Tailwind + HTMX)
│   ├── base.html                  # Layout, nav com página ativa, flash messages
│   ├── login.html / register.html
│   ├── student/                   # dashboard, assignment_detail, grades, submission_status
│   ├── professor/                 # dashboard, assignment_form, assignment_detail,
│   │                              # submission_review, grades_overview, settings,
│   │                              # students_list, student_form
│   └── partials/                  # Fragmentos HTMX (status_indicator, grade_badge)
│
├── scripts/
│   ├── setup.sh                   # Instalação no droplet (Ubuntu 24)
│   ├── deploy.sh                  # Deploy com Nginx + systemd
│   ├── backup.sh                  # Backup SQLite + storage
│   ├── create_admin.py            # Criar conta de professor
│   ├── seed_examples.py           # Popular com exercícios de exemplo
│   └── seed_demo.py               # Seed completo para demonstração (prof + alunos + trabalhos + ZIPs)
│
├── examples/                      # 3 exercícios de exemplo com gabarito
│   ├── 01-contagem-primos/
│   ├── 02-race-condition-fix/
│   └── 03-produtor-consumidor/
│
├── tests/                         # 22 testes automatizados
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_submission.py
│   └── test_grader.py
│
└── storage/                       # Dados persistentes (não versionado)
    ├── db/autograder.db
    ├── submissions/
    └── demo_solutions/            # ZIPs gerados pelo seed_demo.py
```

---

## Instalação Local (Desenvolvimento)

### Pré-requisitos

- Python 3.9+
- gcc (para compilar código dos alunos)
- git (para integração GitHub)
- valgrind (opcional, para Helgrind — disponível apenas em Linux)

### Início rápido

```bash
# 1. Clonar o repositório
git clone <url-do-repo>
cd lpii-autograder

# 2. Criar virtualenv e instalar dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Seed de demonstração (cria professor, alunos, trabalhos e ZIPs de teste)
python scripts/seed_demo.py

# 4. Iniciar o servidor web
python main.py
# Acesse http://localhost:8000

# 5. Iniciar o worker de correção (em outro terminal)
source venv/bin/activate
python grader/worker.py
```

### Contas de demonstração

Criadas pelo `seed_demo.py`:

| Papel | Email | Senha |
|---|---|---|
| Professor | bidu@lavid.ufpb.br | prof123 |
| Aluna | ana@aluno.ufpb.br | aluno123 |
| Aluno | carlos@aluno.ufpb.br | aluno123 |
| Aluna | juliana@aluno.ufpb.br | aluno123 |

### ZIPs de teste para upload

Gerados em `storage/demo_solutions/`:

| Arquivo | Trabalho | Resultado esperado |
|---|---|---|
| `trab1_correto.zip` | Soma de Dois Inteiros | Nota 10.0 |
| `trab1_errado.zip` | Soma de Dois Inteiros | Nota parcial (compila, testes falham) |
| `trab1_nao_compila.zip` | Soma de Dois Inteiros | Nota 0.0 |
| `trab2_correto.zip` | Contador Concorrente | Nota alta (testes + stress OK) |
| `trab2_com_race.zip` | Contador Concorrente | Stress falha, helgrind detecta races |

### Setup manual (sem seed)

```bash
# Criar apenas a conta de professor
python scripts/create_admin.py \
    --name "Prof Bidu" \
    --email bidu@lavid.ufpb.br \
    --password <sua-senha>

# Carregar exercícios de exemplo (3 trabalhos prontos)
python scripts/seed_examples.py
```

### macOS

No macOS o sandbox roda em modo básico (apenas timeout, sem namespace isolation) e o Helgrind não está disponível. Isso é suficiente para desenvolvimento. Em produção no Linux, o modo `unshare` oferece isolamento completo.

---

## Deploy em Produção (Digital Ocean)

### Requisitos do Droplet

- **OS**: Ubuntu 24.04 LTS
- **RAM**: 2GB mínimo (4GB recomendado para Helgrind)
- **Disco**: 25GB SSD
- **Software instalado pelo setup.sh**: Python 3.11+, gcc, valgrind, git, nginx

### Passo a passo

```bash
# 1. No droplet, clonar o projeto
git clone <url-do-repo> /opt/lpii-autograder
cd /opt/lpii-autograder

# 2. Rodar o script de setup (como root)
sudo bash scripts/setup.sh

# 3. Gerar e configurar SECRET_KEY
export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
# Adicionar ao /etc/environment ou ao arquivo de override do systemd

# 4. Criar conta de professor
source /opt/lpii-autograder/venv/bin/activate
python scripts/create_admin.py \
    --name "Prof Bidu" \
    --email bidu@lavid.ufpb.br \
    --password <senha-segura>

# 5. Deploy com Nginx
sudo bash scripts/deploy.sh seudominio.com

# 6. HTTPS com Let's Encrypt
sudo certbot --nginx -d seudominio.com
```

### Serviços systemd

| Serviço | Descrição | Comando |
|---|---|---|
| `autograder.service` | Servidor web (Gunicorn + Uvicorn) | `systemctl status autograder` |
| `autograder-worker.service` | Worker de correção (com crash recovery) | `systemctl status autograder-worker` |

```bash
sudo systemctl restart autograder
sudo systemctl restart autograder-worker
sudo journalctl -u autograder -f        # logs do servidor
sudo journalctl -u autograder-worker -f  # logs do worker
```

### Backup

```bash
# Backup manual
sudo bash scripts/backup.sh

# Backup automático via cron (diário às 3h)
echo "0 3 * * * root /opt/lpii-autograder/scripts/backup.sh" | sudo tee /etc/cron.d/autograder-backup
```

Os backups são salvos em `/var/backups/autograder/` com retenção de 30 dias.

---

## Configuração

Toda a configuração é feita via **variáveis de ambiente** (ou valores padrão em `config.py`).

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | `CHANGE-ME-IN-PRODUCTION` | Chave para assinar cookies de sessão. **Obrigatória em produção.** |
| `DEBUG` | `false` | Modo debug (logs SQL, recarregamento automático) |
| `SITE_URL` | `http://localhost:8000` | URL pública do site |
| `STORAGE_DIR` | `./storage` | Diretório para banco, submissões e trabalhos |
| `SANDBOX_MODE` | `unshare` | Modo de sandbox: `unshare` (Linux), `docker`, `none` |
| `LLM_ENABLED` | `false` | Habilitar análise via LLM |
| `LLM_BASE_URL` | `http://localhost:11434` | URL da API do Ollama |
| `LLM_MODEL` | `qwen2.5-coder:14b` | Modelo do Ollama a usar |
| `GITHUB_TOKEN` | *(vazio)* | Token para acessar repos privados do GitHub |
| `SUBMISSION_RATE_LIMIT` | `30` | Segundos mínimos entre submissões do mesmo aluno |

### Exemplo de configuração em produção

```bash
# /etc/environment ou arquivo de override do systemd
SECRET_KEY=seu-token-hex-de-64-caracteres
SITE_URL=https://autograder.seudominio.com
STORAGE_DIR=/opt/lpii-autograder/storage
SANDBOX_MODE=unshare
LLM_ENABLED=true
LLM_BASE_URL=http://192.168.1.100:11434
LLM_MODEL=qwen2.5-coder:14b
```

---

## Integração com LLM (Ollama)

O sistema pode enviar o código do aluno para uma instância do [Ollama](https://ollama.ai) para análise qualitativa. A LLM avalia:

1. Qualidade e organização do código
2. Uso correto de primitivas de concorrência
3. Bugs de concorrência (race conditions, deadlocks)
4. Sugestões de melhoria

### Configuração

```bash
# Na máquina com GPU (ex: RTX 5070 do professor)
ollama pull qwen2.5-coder:14b
ollama serve  # porta 11434

# Túnel SSH para o droplet (se Ollama não estiver exposto)
ssh -R 11434:localhost:11434 usuario@droplet

# Ou usar Tailscale/WireGuard para acesso direto
```

No droplet:

```bash
export LLM_ENABLED=true
export LLM_BASE_URL=http://localhost:11434  # via túnel
```

Quando a LLM está habilitada em um trabalho, as notas **não são publicadas automaticamente** — o professor precisa revisar o feedback da LLM e publicar manualmente.

---

## Integração com GitHub

Alunos podem submeter via URL de repositório GitHub em vez de upload de ZIP.

### Fluxo

1. Professor habilita "Aceitar submissão via GitHub" no trabalho
2. Aluno informa URL do repositório (ex: `https://github.com/aluno/lpii-trab1`)
3. Sistema verifica acessibilidade do repo antes de aceitar a submissão
4. Worker clona o repo e faz checkout do último commit antes do deadline
5. Correção segue o pipeline normal (compilação, testes, etc.)

### Repos privados

Para acessar repos privados, configure um GitHub Personal Access Token:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

---

## Pipeline de Correção

Quando um aluno submete código, o worker executa o seguinte pipeline:

```
1. PREPARAÇÃO         Clone do GitHub (se aplicável) ou uso do ZIP extraído
       |
2. VALIDAÇÃO          Verificar arquivos esperados, extensões permitidas, tamanho
       |
3. COMPILAÇÃO         gcc {flags} -o {binary} {source}
       |
4. TESTES             Executar binário com argumentos definidos, comparar saída
       |
5. STRESS TEST        Executar N vezes, verificar consistência de resultados
       |
6. HELGRIND           valgrind --tool=helgrind, contar data races
       |
7. LLM (opcional)     Enviar código para Ollama, receber nota + feedback
       |
8. CÁLCULO DE NOTA    Média ponderada normalizada para nota máxima do trabalho
```

### Cálculo da Nota

```
score = compile_ok   * compile_weight
      + tests_score  * tests_weight
      + consistency  * stress_weight
      + helgrind_ok  * helgrind_weight

nota_final = (score / total_weight) * nota_máxima
```

Os pesos são configuráveis por trabalho na interface visual do formulário de criação/edição.

### Crash Recovery

Se o worker cair durante a correção, submissões presas em estados intermediários (`compiling`, `testing`, `grading`) são automaticamente re-enfileiradas na próxima inicialização do worker (ou após 10 minutos via check periódico).

---

## Configuração de Testes (UI Visual)

O formulário de criação/edição de trabalho possui uma interface visual para configurar toda a avaliação, dividida em seções:

1. **Compilação**: flags do gcc, arquivo principal, nome do binário
2. **Pesos**: compilação, testes, stress, helgrind, LLM (inputs numéricos)
3. **Testes funcionais**: adicionar/remover testes dinâmicamente, cada um com nome, argumentos, timeout, saída esperada e pontos
4. **Stress test**: toggle + número de execuções, argumentos, saída esperada
5. **Helgrind**: toggle + argumentos, timeout, erros tolerados
6. **LLM**: toggle + rubrica e contexto para a análise qualitativa

Toda a configuração é salva como JSON no campo `grading_config` do banco, mas o professor nunca precisa editar JSON diretamente.

### Formato do Descritor (referência)

```json
{
  "compile": {
    "entry_point": "primecount.c",
    "binary_name": "primecount"
  },
  "compile_weight": 1.0,
  "tests_weight": 6.0,
  "stress_weight": 1.5,
  "helgrind_weight": 1.0,
  "llm_weight": 0.5,
  "tests": [
    {
      "name": "Sequencial básico",
      "args": ["seq", "1000"],
      "timeout_sec": 10,
      "expected_output_contains": "168",
      "points": 1.0
    }
  ],
  "stress": {
    "enabled": true,
    "runs": 20,
    "args": ["par", "100000", "4", "pipe"],
    "expected_output_contains": "9592",
    "timeout_sec": 15
  },
  "helgrind": {
    "enabled": true,
    "args": ["par", "1000", "2", "pipe"],
    "timeout_sec": 60,
    "max_errors": 0
  }
}
```

### Tipos de comparação de saída

- `expected_output_contains`: a saída deve **conter** o texto especificado
- `expected_output_exact`: a saída deve ser **exatamente** igual
- `expected_output_regex`: a saída deve casar com a expressão regular

---

## Exercícios de Exemplo

O repositório inclui 3 exercícios prontos na pasta `examples/`:

| # | Título | Módulo | Conceitos |
|---|---|---|---|
| 01 | Contagem de Primos Paralela | 1 | fork, pipe, shared memory |
| 02 | Corrigir Race Condition | 2 | threads, mutex |
| 03 | Produtor-Consumidor | 2 | buffer circular, mutex, condvar |

Cada exercício inclui:
- `assignment.json` — descritor completo com testes e configuração
- `enunciado.md` — enunciado em Markdown
- `gabarito/` — solução de referência do professor

Carregar no banco:

```bash
python scripts/seed_examples.py
```

---

## Testes

O projeto inclui 22 testes automatizados cobrindo autenticação, submissão e correção.

```bash
source venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

### Cobertura

- **test_auth.py** (11 testes): login, registro, logout, proteção de rotas, roles
- **test_submission.py** (6 testes): upload ZIP, validação de arquivos, versionamento, rejeição de arquivos inválidos
- **test_grader.py** (5 testes): compilação correta/falha, output correto/errado, stress test, fluxo de revisão do professor

---

## Atores e Fluxos

### Aluno

1. Faz cadastro ou login (conta criada pelo professor ou auto-registro)
2. Visualiza trabalhos publicados com **tempo restante** até o prazo
3. Acessa detalhes do trabalho (enunciado Markdown renderizado)
4. Submete solução (upload ZIP ou link GitHub)
5. Recebe **confirmação visual** da submissão (flash message)
6. Acompanha status em tempo real (polling HTMX: fila > compilando > testando > nota)
7. Visualiza nota, detalhamento por critério e feedback quando publicados
8. Consulta todas as notas na página "Minhas Notas"

### Professor

1. Faz login (conta criada via `create_admin.py` ou `seed_demo.py`)
2. **Gerencia alunos**: cadastrar, editar dados/senha, desativar/reativar (CRUD completo com busca)
3. **Cria trabalhos** com interface visual: enunciado Markdown, testes funcionais (dinâmicos), stress test, Helgrind, LLM, pesos — tudo sem editar JSON
4. Visualiza submissões por trabalho com **busca por nome** e **filtro por status** (Todas, Pendentes, Corrigidas, Erros)
5. Revisa resultado detalhado de cada submissão (compilação, testes, stress, Helgrind, feedback LLM)
6. Ajusta nota final, adiciona comentários, publica — com **confirmação visual**
7. Ações em massa: publicar todas as notas, re-corrigir, exportar CSV
8. Consulta painel de notas com estatísticas (média, mediana, distribuição por trabalho)
9. Visualiza configurações do sistema (LLM, sandbox, worker)

---

## Segurança

### Autenticação e sessão
- Senhas hasheadas com **bcrypt** (12 rounds)
- Sessões assinadas com **itsdangerous** (cookie httponly, samesite=lax, 24h)
- Roles separados (student/professor) com proteção de rotas

### Submissões
- **Rate limiting**: 30s entre submissões do mesmo aluno para o mesmo trabalho
- **Whitelist de extensões**: apenas `.c`, `.h`, `.cpp`, `.cc`, `.hpp`, `.sh`, `.py`, `.txt`, `.md`, `.json`, `Makefile`
- **Proteção contra zip bomb**: verifica razão de compressão (max 100x) e tamanho declarado antes de extrair
- **Path traversal**: resolve caminhos e verifica que ficam dentro do diretório destino
- **Limite de tamanho**: 1MB por arquivo, 10MB total, máximo 200 arquivos por ZIP
- **Limite de submissões**: configurável por trabalho

### GitHub
- URLs validadas contra **command injection** (rejeita `;`, `&`, `|`, `` ` ``, `$`, `(`, `)`)
- Verificação de acessibilidade do repo (`git ls-remote`) antes de aceitar submissão
- Token de acesso via variável de ambiente (nunca no código)

### Execução de código
- Sandbox com limites de CPU, memória, processos e rede
- `unshare` (Linux): isolamento de namespace (PID, rede, mount)
- Timeout wall-clock e CPU-time independentes

---

## Licença

Projeto desenvolvido para uso acadêmico na UFPB.

UFPB / CI / DI — LAViD — Prof. Bidu (Carlos Eduardo C. F. Batista)
