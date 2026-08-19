"""
LLM Connectors using OpenRouter.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Cargar variables de entorno desde .env
load_dotenv()

def get_openrouter_llm(model_name: str, temperature: float = 0.7, timeout: int = 300, max_retries: int = 2) -> ChatOpenAI:
    """
    Inicializa un modelo de lenguaje de OpenRouter usando la interfaz de ChatOpenAI.
    
    Args:
        model_name: Nombre del modelo en OpenRouter (ej. 'google/gemini-2.5-flash')
        temperature: Temperatura para controlar la creatividad (0.0 a 1.0)
        timeout: Tiempo máximo en segundos para esperar la respuesta del modelo
        max_retries: Número de reintentos automáticos ante errores transitorios
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or api_key == "tu_openrouter_api_key_aqui":
        # Levantamos un warning informativo pero devolvemos una instancia que intentará leer de la variable
        print("ADVERTENCIA: OPENROUTER_API_KEY no configurada correctamente en el entorno.")
        
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        timeout=timeout,
        max_retries=max_retries,
        default_headers={
            "HTTP-Referer": "https://github.com/langgraph-sales-agent",
            "X-Title": "LangGraph Sales Marketing Agent"
        }
    )

def get_supervisor_llm() -> ChatOpenAI:
    """Supervisor (CMO) - Gemini 2.5 Flash por velocidad y function calling."""
    return get_openrouter_llm("google/gemini-2.5-flash", temperature=0.1)

def get_researcher_llm() -> ChatOpenAI:
    """Investigador de Mercado - Gemini 2.5 Flash por contexto extenso."""
    return get_openrouter_llm("google/gemini-2.5-flash", temperature=0.2)

def get_copywriter_llm() -> ChatOpenAI:
    """Copywriter - Claude 3.5 Sonnet (o Llama 3.1 70B de respaldo) por creatividad."""
    # Usaremos Claude 3.5 Sonnet como primera opción
    return get_openrouter_llm("mistralai/mistral-large-2512", temperature=0.7)

def get_strategist_llm() -> ChatOpenAI:
    """Estratega SEO y de Canales - Gemini 2.5 Flash por velocidad y fiabilidad."""
    return get_openrouter_llm("google/gemini-2.5-flash", temperature=0.3)
