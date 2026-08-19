# Walkthrough: Sistema Multi-Agente de Marketing y Ventas

Hemos completado la estructuración e implementación del **Sistema Multi-Agente de Marketing** orquestado por un Supervisor en LangGraph. Toda la base de código ha sido verificada y compila correctamente.

---

## Estructura Creada

Hemos organizado el proyecto de manera limpia y modular en [AgenteDeVentas](file:///d:/LangGraph/AgenteDeVentas):

1. **[pyproject.toml](file:///d:/LangGraph/AgenteDeVentas/pyproject.toml)**: Define las dependencias del entorno virtual (LangGraph, Playwright, dotenv).
2. **[.env](file:///d:/LangGraph/AgenteDeVentas/.env)**: Variables de configuración para OpenRouter y la URL CDP de LightPanda.
3. **[src/agente_ventas/state.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/state.py)**: Define el estado compartido (`MarketingState`) del grafo.
4. **[src/agente_ventas/llms.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/llms.py)**: Inicializa los modelos correspondientes en OpenRouter (Gemini, Claude, Llama).
5. **[src/agente_ventas/tools.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/tools.py)**: Herramientas de navegación CDP para buscar y extraer datos usando **LightPanda**.
6. **[src/agente_ventas/prompts.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/prompts.py)**: Prompts del sistema para el Supervisor y los agentes.
7. **[src/agente_ventas/nodes.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/nodes.py)**: Lógica de ejecución de los nodos del grafo.
8. **[src/agente_ventas/graph.py](file:///d:/LangGraph/AgenteDeVentas/src/agente_ventas/graph.py)**: Ensamblaje del flujo de trabajo, transiciones condicionales y persistencia.
9. **[run_campaign.py](file:///d:/LangGraph/AgenteDeVentas/run_campaign.py)**: Script interactivo para ejecutar la campaña en tu consola con formato visual rico.

---

## Instrucciones para Ejecutar la Campaña

Para probar tu nuevo sistema agéntico, sigue estos pasos:

### 1. Configurar tu API Key
Abre el archivo **[.env](file:///d:/LangGraph/AgenteDeVentas/.env)** y reemplaza `tu_openrouter_api_key_aqui` por tu clave de API real de OpenRouter:
```env
OPENROUTER_API_KEY=sk-or-v1-...
```

### 2. Iniciar LightPanda en Docker
Asegúrate de que el contenedor de LightPanda esté encendido para habilitar las búsquedas web del Investigador:
```powershell
docker start lightpanda
```

### 3. Ejecutar el Script
Abre una terminal en `d:/LangGraph/AgenteDeVentas` y lanza la campaña interactiva ejecutando:
```powershell
uv run run_campaign.py
```

El script te preguntará qué deseas vender (ej. *"Servicio de consultoría de IA para e-commerce"*) y verás en tiempo real cómo el Supervisor delega el trabajo, realiza scraping usando LightPanda y genera los borradores de copy y la estrategia SEO.
