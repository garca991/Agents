import streamlit as st
import asyncio
import threading
import uuid
import sys
from google.adk.runners import InMemoryRunner
from google.genai import types
from flights_agent.agent import get_agent

# Configuración de la página
st.set_page_config(
    page_title="AI Travel Concierge",
    page_icon="✈️",
    layout="centered"
)

st.title("Concierge de Viajes AI 🌍")
st.markdown("¡Hola! Soy tu planificador de viajes experto. Puedo ayudarte a buscar vuelos, alojamiento, eventos y restaurantes.")

# --- Configuración Asíncrona Persistente ---
@st.cache_resource
def get_async_loop():
    """Crea un Event Loop que vive en un hilo separado para que no se cierre en cada recarga."""
    loop = asyncio.new_event_loop()
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    thread = threading.Thread(target=start_loop, args=(loop,), daemon=True)
    thread.start()
    return loop

bg_loop = get_async_loop()

APP_NAME = "flights_app"
USER_ID = "user_1"

async def _init_runner():
    # Al llamar a get_agent() aquí, MCPToolset se ancla al bg_loop
    return InMemoryRunner(agent=get_agent(), app_name=APP_NAME)

@st.cache_resource
def get_runner():
    future = asyncio.run_coroutine_threadsafe(_init_runner(), bg_loop)
    return future.result()

runner = get_runner()

# Inicializar sesión
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    # Crear la sesión en el runner asíncronamente en el hilo de fondo
    future = asyncio.run_coroutine_threadsafe(
        runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=st.session_state.session_id
        ),
        bg_loop
    )
    future.result() # Esperar a que termine

# Inicializar el historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¿A dónde te gustaría viajar y en qué fechas?"}
    ]

# Mostrar los mensajes del historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def ask_agent(prompt_text, current_session_id):
    user_message = types.Content(
        role="user", parts=[types.Part.from_text(text=prompt_text)]
    )
    final_text = "Lo siento, no pude encontrar una respuesta."
    
    async for event in runner.run_async(
        user_id=USER_ID, session_id=current_session_id, new_message=user_message
    ):
        if hasattr(event, 'is_final_response') and event.is_final_response():
            if hasattr(event, 'content') and getattr(event.content, 'parts', None):
                final_text = "".join(part.text for part in getattr(event.content, 'parts', []))
            break
            
    return final_text

# Entrada de usuario
if prompt := st.chat_input("Escribe aquí tu destino o duda..."):
    # Agregar mensaje del usuario al chat
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Mostrar spinner mientras el agente procesa
    with st.chat_message("assistant"):
        with st.spinner("Buscando las mejores opciones para ti..."):
            try:
                # Llamar al agente usando el event loop de fondo
                future_response = asyncio.run_coroutine_threadsafe(ask_agent(prompt, st.session_state.session_id), bg_loop)
                response_text = future_response.result() # Espera bloqueando hasta que responda
                
                # Mostrar respuesta
                st.markdown(response_text)
                # Guardar respuesta en el historial
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                error_msg = f"Lo siento, ocurrió un problema al procesar tu solicitud: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
