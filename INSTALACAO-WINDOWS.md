# Guia de Instalação — Windows 11

Este guia cobre a instalação do kb-manager em **Windows 11** com Git Bash. O [README.md](README.md) principal foi escrito para macOS/Linux — este documento registra as diferenças e correções necessárias para Windows.

---

## Pré-requisitos

| Ferramenta | Obrigatório | Como instalar |
|---|---|---|
| **Git for Windows** | Sim | [git-scm.com](https://git-scm.com/download/win) — instala também o Git Bash |
| **Python 3.13+** | Sim | `winget install Python.Python.3.13` no PowerShell, ou baixar em python.org |
| **Google Cloud SDK** (gcloud) | Sim | Ver seção abaixo |
| **gh CLI** | Não | Só necessário para sincronizar repos LookML/Dataform (`sync-repos.sh`) |

> O projeto especifica Python 3.13, mas versões superiores (3.14+) funcionam normalmente. O que importa é que o executável esteja registrado no `.env` via `KB_EVAL_PYTHON`.

---

## 1. Instalar o Google Cloud SDK

O instalador padrão do Google Cloud SDK requer direitos de administrador. Em computadores corporativos sem admin, use o winget com a fonte correta:

```powershell
winget install Google.CloudSDK --source winget
```

> Se aparecer erro de SSL corporativo ao usar `--source msstore`, troque para `--source winget` como acima.

Após a instalação, **feche e reabra o VS Code** para o `gcloud` aparecer no PATH.

Verifique:
```powershell
gcloud --version
```

---

## 2. Autenticar o gcloud (Application Default Credentials)

O MCP do BigQuery usa autenticação via Application Default Credentials (ADC) — não a mesma coisa que o login no navegador. Rode uma vez no PowerShell:

```powershell
gcloud auth application-default login
```

Isso abre o navegador. Faça login com sua conta Google corporativa. Ao concluir, o token fica salvo localmente e o Python usa automaticamente.

Verifique:
```powershell
gcloud auth application-default print-access-token
```
Deve retornar um token longo começando com `ya29.`.

---

## 3. Configurar o arquivo `.env`

Copie o exemplo:
```powershell
copy .env.example .env
```

Edite o `.env` e preencha os valores. No Windows, o campo `KB_EVAL_PYTHON` é **obrigatório** e deve apontar para o executável Python no formato Git Bash (barras `/c/...`):

```env
BIGQUERY_PROJECT_ID=seu-projeto-bq

# Caminho do Python no formato Git Bash — ajuste para o seu usuário
KB_EVAL_PYTHON=/c/Users/SEU_USUARIO/AppData/Local/Python/pythoncore-3.14-64/python.exe

# Looker (opcional)
LOOKERSDK_BASE_URL=https://sua-instancia.cloud.looker.com
LOOKERSDK_CLIENT_ID=seu-client-id
LOOKERSDK_CLIENT_SECRET=seu-client-secret

# Metabase (opcional)
METABASE_URL=https://seu-metabase.com
METABASE_API_KEY=mb_sua-chave

# GitHub (opcional — para sync-repos.sh)
KB_GITHUB_ORG=SuaOrg
KB_GITHUB_REPOS="repo1 repo2"
```

> Para descobrir o caminho correto do Python, rode no PowerShell: `(Get-Command python).Source`

---

## 4. Correções necessárias no `setup-mcp.sh`

O script foi escrito para macOS. Antes de rodar no Windows, aplique as três correções abaixo. O arquivo já está corrigido neste repositório — esta seção documenta o que foi mudado e por quê.

### Correção 1 — Python path lido do `.env`

**Problema:** A linha que define `PYTHON_BIN` estava antes do `source "$PROJECT_ROOT/.env"`, então a variável `KB_EVAL_PYTHON` do `.env` nunca era lida. O script tentava usar `/opt/homebrew/bin/python3.13` (path do macOS) e falhava.

**Solução:** mover a definição de `PYTHON_BIN` para depois do bloco que carrega o `.env`:

```bash
# ANTES (quebrado no Windows):
PYTHON_BIN="${KB_EVAL_PYTHON:-/opt/homebrew/bin/python3.13}"
# ...depois vinha source "$PROJECT_ROOT/.env"

# DEPOIS (correto):
source "$PROJECT_ROOT/.env"
# ...
PYTHON_BIN="${KB_EVAL_PYTHON:-/opt/homebrew/bin/python3.13}"
```

### Correção 2 — Diretório do venv: `Scripts/` em vez de `bin/`

**Problema:** No Windows, o Python cria venvs com `Scripts/` em vez de `bin/`. O script chamava `mcp-bq/.venv/bin/pip` que não existia no Windows.

**Solução:** adicionar detecção do OS e usar a variável `$VENV_BIN`:

```bash
# Detectar Windows (Git Bash) — venvs usam Scripts/ em vez de bin/
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || -n "${WINDIR:-}" ]]; then
  VENV_BIN="Scripts"
else
  VENV_BIN="bin"
fi
```

E substituir todas as referências a `bin/python` e `bin/pip` por `$VENV_BIN/python`.

### Correção 3 — Upgrade do pip via módulo Python

**Problema:** No Windows, `pip install --upgrade pip` falha com a mensagem:
```
ERROR: To modify pip, please run: python.exe -m pip install --upgrade pip
```

**Solução:** usar `python -m pip install --upgrade pip` em vez de chamar pip diretamente:

```bash
# ANTES:
"$dest/.venv/bin/pip" install --quiet --upgrade pip

# DEPOIS:
"$dest/.venv/$VENV_BIN/python" -m pip install --quiet --upgrade pip
```

### Correção 4 — BigQuery MCP trava (gcloud como subprocess)

**Problema:** O MCP do BigQuery ficava rodando indefinidamente (5+ minutos) sem retornar resultado. A causa raiz é que a biblioteca `google-auth` chama `gcloud config get-value project` como subprocesso ao inicializar credenciais. No contexto MCP (stdin/stdout piped ao Claude Code), esse subprocesso herda o pipe e trava aguardando stdin que nunca chega.

**Diagnóstico:** Watchdog thread no servidor revelou o stack trace:
```
google.auth._cloud_sdk.get_project_id()
  subprocess.check_output(['gcloud', 'config', 'get-value', 'project'], ...)
```

**Solução:** Em `.claude-plugin/mcps/bq/server.py`, a função `_client()` carrega as credenciais diretamente do arquivo ADC JSON, evitando qualquer chamada ao `gcloud`:

```python
def _client(project_id: str) -> bigquery.Client:
    adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if adc and os.path.isfile(adc):
        from google.oauth2 import credentials as oauth2_credentials
        creds = oauth2_credentials.Credentials.from_authorized_user_file(
            adc, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return bigquery.Client(project=project_id, credentials=creds)
    return bigquery.Client(project=project_id)
```

O `setup-mcp.sh` agora detecta automaticamente o caminho do arquivo ADC por plataforma e injeta `GOOGLE_APPLICATION_CREDENTIALS` e `GOOGLE_CLOUD_PROJECT` no env do bq_local em `~/.claude.json`.

### Correção 5 — SSL corporativo (proxy com certificado próprio)

**Problema:** Em redes corporativas com proxy SSL (firewall que intercepta HTTPS com certificado próprio), os MCPs Looker e Metabase falham ao conectar:
```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain'))
```

Tentativas de simplesmente desabilitar a verificação (`LOOKERSDK_VERIFY_SSL=false`) levam a outro erro porque o SDK trata a string `"false"` como caminho de arquivo:
```
Connection broken: FileNotFoundError(2, 'No such file or directory')
```

**Solução:** usar o pacote `truststore`, que faz o Python usar o **certificate store do sistema operacional** (Windows Certificate Store). Como o proxy corporativo já injetou seu CA nesse store, a verificação funciona normalmente.

Mudanças aplicadas:

1. Em `.claude-plugin/mcps/looker/server.py` e `.claude-plugin/mcps/metabase/server.py`, no topo do arquivo (antes de qualquer import que use HTTP):

```python
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
```

2. Em `.claude-plugin/mcps/looker/requirements.txt` e `.claude-plugin/mcps/metabase/requirements.txt`:

```
truststore
```

Após essas mudanças, basta rodar `./setup-mcp.sh` novamente — o pacote é instalado no venv automaticamente.

> **Nota:** A correção 4 (gcloud subprocess) não requer truststore — são problemas diferentes. A correção 4 é para o BigQuery; a correção 5 (truststore) é para Looker e Metabase.

---

## 5. Rodar o setup

O script deve ser executado no **Git Bash** (não no PowerShell). No VS Code, abra um terminal Git Bash e rode:

```bash
./setup-mcp.sh
```

Saída esperada ao final:
```
✓ mcp-bq pronto
✓ mcp-looker pronto
✓ mcp-metabase pronto
✓ MCP bq_local registrado (BIGQUERY_PROJECT_ID=seu-projeto)
✓ MCP looker_local registrado (...)
✓ MCP metabase_local registrado (...)

Pronto. Reinicie o Claude Code para os MCPs entrarem em efeito.
```

---

## 6. Reiniciar o Claude Code

Após o `setup-mcp.sh` concluir, **feche e reabra o VS Code**. Os MCPs e os slash commands (`/create-kb`, `/run-eval`) são carregados na inicialização.

---

## Solução de problemas

| Erro | Causa provável | Solução |
|---|---|---|
| `gcloud: command not found` | PATH não atualizado após instalação | Fechar e reabrir o VS Code |
| `Your default credentials were not found` | ADC não configurado | Rodar `gcloud auth application-default login` |
| `/opt/homebrew/bin/python3.13: No such file` | `KB_EVAL_PYTHON` não definido no `.env` ou `PYTHON_BIN` definido antes do source | Verificar correção 1 e adicionar `KB_EVAL_PYTHON` no `.env` |
| `mcp-bq/.venv/bin/pip: No such file` | Venv no Windows usa `Scripts/` | Verificar correção 2 |
| `To modify pip, please run: python.exe -m pip` | pip no Windows exige chamada via módulo | Verificar correção 3 |
| `winget` com erro de SSL | Rede corporativa bloqueia msstore | Usar `winget install ... --source winget` |
| `gh repo clone` falha | SSO da org não autorizado para o token | Rodar `gh repo view ORG/repo` para acionar o prompt de autorização |
| MCP não responde no Claude Code | Credencial vazia ou gcloud expirado | Verificar `.env` e rodar `gcloud auth application-default login` novamente |
| BQ MCP trava por 5+ minutos sem resposta | `gcloud` chamado como subprocess bloqueia no pipe MCP | Aplicar correção 4 (`_client()` carrega ADC direto do arquivo) |
| `SSLCertVerificationError: self-signed certificate in certificate chain` | Proxy corporativo SSL | Aplicar correção 5 (truststore) |
| `Connection broken: FileNotFoundError` (depois de tentar desabilitar SSL) | SDK trata `"false"` como caminho | Não desabilitar SSL — usar truststore (correção 5) |
