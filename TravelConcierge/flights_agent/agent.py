import os
import asyncio
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

load_dotenv()

# Configuración del servidor MCP
current_dir = os.path.dirname(os.path.abspath(__file__))
mcp_script = os.path.join(current_dir, "mcp_server.py")

def get_agent():
    flights_mcp_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=[mcp_script],
            ),
            timeout=30.0,
        ),
    )

    # Definición del Agente
    root_agent = Agent(
        name="agente_vuelos",
        model=os.getenv("MODEL", "gemini-2.5-flash"),
        description="Un agente Concierge de Viajes experto en planificar vuelos, hoteles, eventos y lugares turísticos usando SerpApi.",
        instruction="""
        Eres un Concierge de Viajes integral y experto. Tu objetivo es planificar viajes completos o asistir en partes específicas según lo pida el usuario.
        Tienes acceso a múltiples herramientas (vuelos, hoteles, eventos y lugares).
        
        INSTRUCCIONES DE ORQUESTACIÓN:
        1. Analiza lo que pide el usuario. Si es un viaje completo, organiza la búsqueda en este orden lógico: vuelos -> hoteles -> eventos/atracciones. No asumas fechas ni destinos, pregúntalos si faltan.
        2. Usa 'search_flights' para buscar opciones aéreas. Recuerda pedir origen, destino y fechas. Intenta inferir códigos IATA.
        3. Usa 'search_hotels' para buscar alojamiento en el destino durante las fechas del viaje.
        4. Usa 'search_events' para descubrir qué está pasando en la ciudad durante las fechas de la visita.
        5. Usa 'search_local_places' para recomendar restaurantes o atracciones locales.
        6. Presenta los resultados de forma estructurada, atractiva y profesional. Agrupa la información (ej. sección de vuelos, sección de hotel).
        7. Siempre responde en español de forma entusiasta y servicial.
        """,
        tools=[flights_mcp_toolset],
    )
    return root_agent

async def main():
    import uuid
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    print("--- Agente de Vuelos ADK Iniciado ---")
    APP_NAME = "flights_cli"
    USER_ID = "user_1"
    SESSION_ID = str(uuid.uuid4())
    
    # Creamos el agente dentro del entorno asíncrono actual
    root_agent = get_agent()
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    while True:
        user_input = input("\nUsuario: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break
        
        user_message = types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
        final_text = ""
        async for event in runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=user_message
        ):
            if hasattr(event, 'is_final_response') and event.is_final_response():
                if hasattr(event, 'content') and getattr(event.content, 'parts', None):
                    final_text = "".join(part.text for part in getattr(event.content, 'parts', []))
                break
                
        print(f"\nAgente: {final_text}")

if __name__ == "__main__":
    asyncio.run(main())
