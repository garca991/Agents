# Sistema Multi-Agente de Marketing y Ventas

Sistema agéntico orquestado por LangGraph que genera automáticamente una campaña de marketing completa: investigación de mercado, estrategia SEO, y copy persuasivo.

## Arquitectura

```
                    ┌─────────────┐
                    │  Supervisor │
                    │    (CMO)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌──────────────┐ ┌──────────┐ ┌───────────┐
     │ Investigador │ │ Copywriter│ │ Estratega │
     │  de Mercado  │ │ Creativo  │ │  de SEO   │
     └──────────────┘ └──────────┘ └───────────┘
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ┌─────────────┐
                    │  Resultado  │
                    │  final (.txt)│
                    └─────────────┘
```

El **Supervisor (CMO)** coordina el flujo, decide qué agente ejecutar en cada paso, evalúa la calidad de los entregables y finaliza la campaña cuando todo está completo.

### Agentes

| Agente | Rol | Modelo |
|--------|-----|--------|
| **Supervisor (CMO)** | Coordina, evalúa y decide el siguiente paso | Gemini 2.5 Flash |
| **Investigador** | Scraping web de competidores, dolores y precios | Gemini 2.5 Flash |
| **Copywriter** | Anuncios, secuencia de correos y landing page | Mistral Large |
| **Estratega** | Plan de canales, palabras clave e ideas de blog | Gemini 2.5 Flash |

### Lógica del Supervisor

- **Límite de llamadas por agente**: máximo 3 invocaciones por agente (tope anti-bucle).
- **Aprobación**: si un agente entregó bien su trabajo y el supervisor lo aprueba (feedback sin pedir cambios), no se le vuelve a llamar aunque le queden llamadas.
- **Re-consulta**: si el supervisor elige un agente agotado o aprobado, se le re-consulta para que elija otro con instrucciones reales (sin saltar directo).
- **Gate de calidad**: el supervisor no puede avanzar a copywriter o estratega si el reporte de investigación tiene menos de 250 caracteres.
- **Fallback LLM**: si el scraping del investigador no obtiene datos suficientes, genera un reporte basado en el conocimiento del modelo para que nunca se avance con datos vacíos.

## Requisitos

- Python 3.11+
- Docker (para LightPanda)
- Cuenta en [OpenRouter](https://openrouter.ai/) con una API key

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/agents.git
cd agents/AgenteDeVentas
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
.\.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -e .
```

### 3. Instalar navegadores de Playwright

```bash
playwright install
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
OPENROUTER_API_KEY=tu_api_key_aqui
LIGHTPANDA_CDP_URL=ws://localhost:9222
```

### 5. Levantar LightPanda en Docker

LightPanda es un navegador headless que expone Chrome DevTools Protocol (CDP) para scraping.

```bash
docker pull lightpanda/lightpanda:latest
docker run -d --name lightpanda -p 9222:9222 lightpanda/lightpanda:latest
```

Verificar que esté escuchando:

```bash
curl http://localhost:9222
```

Si usas Docker Desktop en Windows, el agente se conecta automáticamente via `host.docker.internal:9222`.

## Ejecutar

```bash
# Con uv (recomendado)
uv run run_campaign.py

# O directamente con Python
python run_campaign.py
```

El script te pedirá el producto o servicio a promocionar y ejecutará la campaña en tiempo real, mostrando cada paso en consola.

Ejemplo:
```
¿Qué producto o servicio deseas promocionar hoy?
> un servicio de consultoría de marketing para pymes
```

Al finalizar, se genera automáticamente el archivo `resultado_campana.txt` con el reporte completo de la campaña.

## Estructura del proyecto

```
AgenteDeVentas/
├── .env                          # Variables de entorno (API keys, URLs)
├── .gitignore
├── pyproject.toml                # Dependencias y configuración del paquete
├── run_campaign.py               # Script principal interactivo
├── src/
│   └── agente_ventas/
│       ├── __init__.py
│       ├── state.py              # Estado compartido del grafo (MarketingState)
│       ├── graph.py              # Ensamblaje del grafo LangGraph
│       ├── nodes.py              # Lógica de cada nodo (supervisor, agentes)
│       ├── llms.py               # Conectores a OpenRouter (configuración de modelos)
│       ├── tools.py              # Herramientas de scraping (LightPanda + Playwright)
│       └── prompts.py            # Prompts del sistema para cada agente
└── tests/
    ├── test_loop_limit.py        # Tests de lógica del supervisor
    ├── test_tools.py             # Tests de herramientas de scraping
    └── test_lightpanda_tools.py  # Tests de conexión con LightPanda
```

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Clave de API de OpenRouter | `sk-or-v1-...` |
| `LIGHTPANDA_CDP_URL` | URL del CDP de LightPanda | `ws://localhost:9222` |
| `LIGHTPANDA_NAV_TIMEOUT_MS` | Timeout de navegación en ms (opcional, default: 60000) | `60000` |
| `LIGHTPANDA_HTTP_TIMEOUT_S` | Timeout HTTP en segundos (opcional, default: 30) | `30` |
| `LIGHTPANDA_MAX_RETRIES` | Reintentos ante fallos (opcional, default: 3) | `3` |

## Ejecutar tests

```bash
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Tecnologías

- **LangGraph** — Orquestación de grafo de agentes con estado y persistencia
- **LangChain** — Framework para LLMs y agentes ReAct
- **OpenRouter** — Gateway unificado a múltiples modelos (Gemini, Mistral, Llama)
- **LightPanda** — Navegador headless via CDP para scraping sin dependencias pesadas
- **Playwright** — Conexión CDP a LightPanda y fallback a navegadores locales
- **Pydantic** — Validación de estructuras de salida de los LLMs
- **Rich** — Visualización rica en terminal
