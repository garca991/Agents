"""
State Definitions for the Marketing Sales Agent.
"""

from typing import Annotated, Sequence, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class MarketingState(TypedDict):
    """
    State for the marketing sales multi-agent system.
    """
    # El producto o servicio que se quiere promocionar
    product_description: str
    
    # Reporte de investigación de mercado y competidores creado por el Investigador
    market_research: str
    
    # Plan de canales de distribución y palabras clave (SEO) creado por el Estratega
    seo_channels_plan: str
    
    # Borradores de textos persuasivos (anuncios, correos, landing) creados por el Copywriter
    copywriting_drafts: Dict[str, str]
    
    # Retroalimentación o correcciones dadas por el Supervisor a los agentes
    supervisor_feedback: str
    
    # Próximo nodo a ejecutar decidido por el Supervisor (investigador, copywriter, estratega, FIN)
    next_agent: str

    # Motivo de finalización del flujo (por ejemplo: completed o in_progress)
    completion_reason: str

    # Contador de llamadas por agente (para limitar a MAX_CALLS_PER_AGENT y prevenir bucles)
    agent_call_counts: Dict[str, int]
    
    # Mensajes de coordinación e historial del flujo
    messages: Annotated[Sequence[BaseMessage], add_messages]
