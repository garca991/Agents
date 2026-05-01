# ✈️ AI Travel Concierge (FlightsAgent)

Un asistente de inteligencia artificial avanzado construido con **Google ADK** (Agent Development Kit) y **Streamlit** que te ayuda a planificar viajes. Es capaz de orquestar búsquedas de vuelos, hoteles, eventos locales y restaurantes usando herramientas basadas en el protocolo **MCP** conectadas a **SerpApi**.

## Características Principales
*   **Agente Conversacional:** Funciona con un hilo asíncrono persistente (`InMemoryRunner`) que mantiene el contexto de tu sesión.
*   **Protocolo MCP Integrado:** Utiliza un servidor local MCP (`mcp_server.py`) que expone herramientas nativas.
*   **Interfaz de Usuario Elegante:** Implementado con Streamlit para un uso fluido e interactivo en el navegador.

## Requisitos Previos
*   Python 3.10 o superior.
*   Una API Key de **SerpApi**.
*   Una API Key de **Google Gemini** (u otro modelo compatible configurado en ADK).

## Configuración Inicial

1. Clona este repositorio.
2. Crea tu entorno virtual y actívalo:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Linux/Mac
   # .venv\Scripts\Activate.ps1 # En Windows
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Crea un archivo `.env` en la raíz del proyecto basándote en este formato:
   ```env
   SERPAPI_KEY=tu_api_key_de_serpapi
   MODEL=gemini-2.5-flash
   ```

## Cómo ejecutar la aplicación

Para arrancar la interfaz web interactiva, ejecuta el siguiente comando:

```bash
streamlit run app.py
```

### Ejecución en Terminal (Modo CLI)
Si prefieres interactuar con el asistente únicamente mediante la consola, puedes usar el script secundario:
```bash
python flights_agent/agent.py
```

## Arquitectura del Proyecto
- `app.py`: Frontend de Streamlit y gestor de estado concurrente para comunicarse con el agente.
- `flights_agent/agent.py`: Inicialización segura del Agente y orquestación de herramientas.
- `flights_agent/mcp_server.py`: El servidor subyacente que intercepta las peticiones del Agente y las transforma en solicitudes hacia SerpApi.
