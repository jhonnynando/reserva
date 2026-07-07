# Sistema de Reservas de Hoteis

Sistema web em Python com Streamlit e PostgreSQL Neon para registrar, consultar, editar, importar e analisar reservas de hoteis para motoristas e ajudantes.

O sistema funciona em modo aberto, sem tela de login.

## 1. Criar o banco no Neon

1. Acesse `https://neon.tech`.
2. Crie uma conta ou entre na conta existente.
3. Crie um novo projeto.
4. Use o banco padrao `neondb` ou crie outro banco.
5. No painel do projeto, acesse **Connection Details**.

O sistema cria as tabelas automaticamente na primeira execucao usando `migrations/schema.sql`.

## 2. Copiar a connection string

No Neon, copie a connection string no formato PostgreSQL:

```text
postgresql://usuario:senha@host/neondb?sslmode=require
```

Use `sslmode=require`, pois o Neon exige conexao segura.

## 3. Configurar o `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edite o `.env`:

```env
DATABASE_URL=postgresql://usuario:senha@host/neondb?sslmode=require
```

Nao coloque a URL real do banco dentro do codigo.

## 4. Instalar dependencias

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale:

```bash
pip install -r requirements.txt
```

## 5. Executar localmente

```bash
streamlit run app.py
```

Na primeira execucao, o sistema conecta no Neon e cria as tabelas e indices se ainda nao existirem.

## 6. Publicar no Streamlit Community Cloud

1. Envie estes arquivos para um repositorio GitHub.
2. Acesse `https://share.streamlit.io`.
3. Crie um novo app apontando para o repositorio.
4. Use `app.py` como arquivo principal.
5. Em **App settings > Secrets**, configure:

```toml
DATABASE_URL = "postgresql://usuario:senha@host/neondb?sslmode=require"
```

## 7. Publicar no Render

1. Crie um novo **Web Service** no Render.
2. Conecte o repositorio GitHub.
3. Configure:

```text
Build Command: pip install -r requirements.txt
Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

4. Em **Environment**, adicione:

```text
DATABASE_URL=postgresql://usuario:senha@host/neondb?sslmode=require
```

## 8. Secrets em producao

O sistema le configuracoes nesta ordem:

1. `st.secrets`, usado pelo Streamlit Community Cloud;
2. variaveis de ambiente, usadas localmente, no Render ou em servidor proprio.

Nunca versione o arquivo `.env`.

## 9. Importar a planilha existente

1. Acesse **Importar Excel**.
2. Envie uma planilha `.xlsx`.
3. Selecione uma ou mais abas, inclusive `HOTEIS2025` e `HOTEIS2026` quando existirem.
4. Clique em **Analisar planilha**.
5. Confira a previa, erros e duplicidades.
6. Escolha se deseja ignorar duplicados ou atualizar registros existentes.
7. Clique em **Importar registros validos**.

A importacao usa transacao. Se houver erro grave durante a gravacao, o lote e cancelado sem importacao parcial.

## Estrutura

```text
app.py
database.py
pages/
  1_Cadastro.py
  2_Reservas.py
  3_Dashboard.py
  4_Importar_Excel.py
services/
  reserva_service.py
  importacao_service.py
utils/
  formatacao.py
  validacao.py
  ui.py
migrations/
  schema.sql
.env.example
requirements.txt
runtime.txt
```

## Observacoes tecnicas

- O banco principal e sempre PostgreSQL Neon.
- As consultas usam parametros `%s` do `psycopg`.
- A conexao e reutilizada com `st.cache_resource`.
- Valores monetarios sao gravados como `NUMERIC(12,2)`.
- A interface usa filtros que recalculam totais apenas sobre os dados filtrados.
- O sistema nao tem login; qualquer pessoa com acesso ao app consegue cadastrar, editar, excluir, importar e consultar dados.
