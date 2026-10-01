# ☕ CaféBot — Agente de café con Mastra

Asistente virtual de una tienda de café de especialidad ("Café de Altura"),
construido como proyecto de aprendizaje con [Mastra](https://mastra.ai).

Incluye un agente conversacional con herramientas, memoria, guardrails,
observabilidad, evaluación (scorers/experimentos), sub-agentes (RAG y búsqueda)
y un frontend propio con login.

## ✨ Funcionalidades

- **Agente CaféBot**: catálogo, pedidos y estado de envíos (tools vía MCP).
- **Workflow de pedidos**: validación + stock + creación determinista.
- **Memoria en 3 capas**: historial, *working memory* (ficha del cliente) y
  *semantic recall* (búsqueda por significado entre conversaciones).
- **Guardrails**: bloqueo de *prompt injection* y de precios inventados.
- **Observabilidad**: trazas de agente, tools, MCP y processors.
- **Evals**: scorer de integridad de precios + datasets + experimentos.
- **Sub-agentes**:
  - `coffeeExpert` — barista con **RAG** sobre recetas (vector store LibSQL).
  - `coffeeScout` — explorador con **Wikipedia** (tool).
- **Auth por JWT** + pantalla de **login** (demo) en el frontend.

## 🏗️ Arquitectura

```
CaféBot (orquestador)
 ├── tools MCP (catálogo / pedidos)      → mcp-server/
 ├── workflow de pedidos
 ├── memoria (SQLite + vectores)
 ├── guardrails (processors)
 ├── observabilidad
 ├── evals (scorer + dataset + experiment)
 ├── coffeeExpert  (RAG de recetas)      → tools/recipe-search
 └── coffeeScout   (Wikipedia)           → tools/wikipedia

Frontend (React + Vite)  ──@mastra/client-js──►  Servidor Mastra
```

## ✅ Requisitos

- Node.js 20+
- Una API key de [OpenRouter](https://openrouter.ai/keys) (modelos + embeddings)

## 🚀 Puesta en marcha

1. **Backend**
   ```bash
   npm install
   cp .env.example .env.development   # y rellena OPENROUTER_API_KEY + MASTRA_JWT_SECRET
   ```

2. **Indexar las recetas** (una vez, para el barista RAG)
   ```bash
   node scripts/ingest-recetas.ts
   ```

3. **Arrancar el backend**
   ```bash
   npm run dev            # http://localhost:4111
   ```

4. **Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   npm run dev            # http://localhost:5173
   ```

## 👤 Usuarios demo (login)

| Usuario | Contraseña |
|---|---|
| `juan-carlos` | `cafe123` |
| `ana-lopez` | `cafe123` |

> El login es **demo**: los usuarios están fijos en `src/mastra/auth/login-route.ts`.
> Para producción: base de datos de usuarios (con hash) o un IdP (Clerk, Supabase…).

## 📁 Estructura

```
src/mastra/
  index.ts                 # Mastra: agents, workflows, storage, observability, server(auth + login)
  storage.ts / vector.ts   # SQLite (libSQL) + vector store
  embedder.ts              # adaptador de embeddings
  auth/                    # loginRoute + firma JWT
  agents/                  # cafebot-agent, coffee-expert, coffee-scout
  workflows/               # order-workflow
  processors/              # guardrails
  tools/                   # recipe-search (RAG), wikipedia
  scorers/                 # price-scorer (evals)
  knowledge/               # recetas-cafe.md
mcp-server/                # servidor MCP de la tienda (catálogo + pedidos)
frontend/                  # app React (login + chat con streaming)
scripts/                   # utilidades: ingesta, pruebas, experimentos
```

## 📝 Notas

- La memoria y las trazas se guardan en `data/cafebot.db` (fuera del control de
  versiones).
- Los scripts de `scripts/` (`test-*.ts`, `experiment-*.ts`) sirven para probar
  cada pieza por separado.
