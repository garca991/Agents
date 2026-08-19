"""
Agent nodes representing Supervisor, Researcher, Copywriter, and SEO Strategist.
"""

import logging
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from agente_ventas.state import MarketingState

logger = logging.getLogger(__name__)
from agente_ventas.llms import (
    get_supervisor_llm,
    get_researcher_llm,
    get_copywriter_llm,
    get_strategist_llm,
)
from agente_ventas.tools import search_web_lightpanda, scrape_website_lightpanda
from agente_ventas.prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    COPYWRITER_SYSTEM_PROMPT,
    STRATEGIST_SYSTEM_PROMPT,
)

# ===== PYDANTIC OUTOUT SCHEMAS FOR STRUCTURED LLM CALLS =====

class SupervisorOutput(BaseModel):
    """Esquema de salida estructurada para las decisiones del Supervisor (CMO)."""
    next_agent: Literal["investigador", "copywriter", "estratega", "FIN"] = Field(
        description="El siguiente agente especialista a invocar. Si la campaña está completa y es de calidad, selecciona 'FIN'."
    )
    feedback: str = Field(
        description="Instrucciones detalladas y específicas para el próximo agente seleccionado. Si regresas una tarea a corrección, detalla los cambios requeridos."
    )

class CopywriterOutput(BaseModel):
    """Esquema de salida estructurada para el Copywriter Creativo."""
    anuncios: str = Field(
        description="Borradores de anuncios persuasivos para redes sociales (variantes con ganchos y CTAs)."
    )
    emails: str = Field(
        description="Secuencia de al menos 3 correos de venta (introducción, agitación del dolor y solución, urgencia/cierre)."
    )
    landing: str = Field(
        description="Estructura de secciones de la Landing Page (títulos, subtítulos, beneficios clave y llamados a la acción)."
    )

# ===== AGENT NODE FUNCTIONS =====

# Agentes en orden de ejecución preferido
_AGENT_ORDER = ["investigador", "estratega", "copywriter"]

# Máximo número de veces que se puede invocar a cada agente (tope anti-bucle)
MAX_CALLS_PER_AGENT = 3

# Longitud mínima del reporte de investigación para considerarlo válido
MIN_RESEARCH_LENGTH = 250

# Palabras que indican que el feedback pide cambios específicos
_CHANGE_INDICATORS = [
    "corregir", "revisar", "mejorar", "cambiar", "modificar",
    "ajustar", "reescribir", "completar", "añadir", "incluir",
]


def _agent_has_delivered(state: MarketingState, agent_name: str) -> bool:
    """Verifica si un agente ya ha entregado su trabajo."""
    if agent_name == "investigador":
        research = state.get("market_research") or ""
        return len(research) > 50 and "No disponible" not in research
    elif agent_name == "estratega":
        plan = state.get("seo_channels_plan") or ""
        return len(plan) > 50 and "No disponible" not in plan
    elif agent_name == "copywriter":
        drafts = state.get("copywriting_drafts") or {}
        return len(drafts) > 0
    return False


def _feedback_asks_for_changes(feedback: str) -> bool:
    """Verifica si el feedback del supervisor pide cambios específicos."""
    feedback_lower = feedback.lower()
    return any(indicator in feedback_lower for indicator in _CHANGE_INDICATORS)


def _next_pending_agent(state: MarketingState, agent_call_counts: dict) -> str | None:
    """Devuelve el primer agente que aún no ha entregado y tiene cupo de llamadas."""
    for agent in _AGENT_ORDER:
        if (not _agent_has_delivered(state, agent)
                and agent_call_counts.get(agent, 0) < MAX_CALLS_PER_AGENT):
            return agent
    return None


def _agent_is_callable(state: MarketingState, agent_call_counts: dict, agent_name: str, feedback: str) -> bool:
    """Indica si el supervisor puede enrutar al agente (tiene cupo y no fue aprobado)."""
    if agent_name == "FIN":
        return False
    if agent_call_counts.get(agent_name, 0) >= MAX_CALLS_PER_AGENT:
        return False
    if _agent_has_delivered(state, agent_name) and not _feedback_asks_for_changes(feedback):
        return False
    return True


def _apply_research_gate(response, state):
    """Aplica el gate de calidad de investigación a la decisión del supervisor.
    Si el research es insuficiente y el agente elegido no es investigador ni FIN,
    fuerza el reenvío al investigador."""
    if response.next_agent not in ("investigador", "FIN"):
        research = state.get("market_research") or ""
        if len(research) < MIN_RESEARCH_LENGTH or "No disponible" in research:
            response.next_agent = "investigador"
            response.feedback = (
                "El reporte de investigación anterior es insuficiente o está incompleto. "
                "Realiza un estudio de mercado completo con herramientas de búsqueda y scraping "
                "que incluya competidores, dolores del cliente, precios y fuentes."
            )
    return response


def supervisor_node(state: MarketingState):
    """
    Nodo Supervisor (CMO).
    Evalúa el estado actual de la campaña y delega al siguiente agente o finaliza.
    """
    # Formatear el diccionario de copies para mostrarlos de forma clara en el prompt
    drafts_str = ""
    if state.get("copywriting_drafts"):
        for key, val in state["copywriting_drafts"].items():
            drafts_str += f"\n--- {key.upper()} ---\n{val}\n"
    else:
        drafts_str = "No disponible aún."
        
    # Formatear el prompt del Supervisor con los datos acumulados
    prompt = SUPERVISOR_SYSTEM_PROMPT.format(
        product_description=state["product_description"],
        market_research=state.get("market_research") or "No disponible aún.",
        seo_channels_plan=state.get("seo_channels_plan") or "No disponible aún.",
        copywriting_drafts=drafts_str,
        supervisor_feedback=state.get("supervisor_feedback") or "Ninguno."
    )
    
    # Obtener LLM y enlazar la salida estructurada
    llm = get_supervisor_llm()
    structured_llm = llm.with_structured_output(SupervisorOutput)
    
    # Invocar al supervisor
    messages_input = [SystemMessage(content=prompt)]
    response = structured_llm.invoke(messages_input)

    # Lógica de ruteo del supervisor:
    #   - Si el agente elegido ya entregó y el feedback NO pide cambios → fue
    #     aprobado: no se le vuelve a llamar aunque tenga cupo.
    #   - Si el agente elegido alcanzó su cuota → tampoco se le puede llamar.
    #   - En ambos casos se re-consulta al supervisor para que decida con
    #     instrucciones reales; el redireccionamiento forzado queda solo como
    #     fallback de seguridad anti-bucle.
    agent_call_counts = state.get("agent_call_counts", {})
    agent_name = response.next_agent

    response = _apply_research_gate(response, state)
    agent_name = response.next_agent

    if agent_name != "FIN" and not _agent_is_callable(state, agent_call_counts, agent_name, response.feedback):
        if agent_call_counts.get(agent_name, 0) >= MAX_CALLS_PER_AGENT:
            reason = f"ya alcanzó su máximo de llamadas ({MAX_CALLS_PER_AGENT})"
        else:
            reason = "ya entregó su trabajo y fue aprobado; solo podría reenviársele si el feedback pidiera cambios específicos"
        available = [a for a in _AGENT_ORDER if agent_call_counts.get(a, 0) < MAX_CALLS_PER_AGENT]
        note = (
            f"ATENCIÓN: El agente '{agent_name}' NO está disponible porque {reason}.\n"
            f"Agentes disponibles: {', '.join(available) if available else 'ninguno (todos agotaron su cupo)'}.\n"
            "Decide el siguiente paso y proporciona instrucciones detalladas."
        )
        retry = structured_llm.invoke(
            [SystemMessage(content=prompt), HumanMessage(content=note)]
        )
        retry = _apply_research_gate(retry, state)
        retry_agent = retry.next_agent
        if retry_agent != "FIN" and _agent_is_callable(state, agent_call_counts, retry_agent, retry.feedback):
            response = retry
            agent_call_counts[retry_agent] = agent_call_counts.get(retry_agent, 0) + 1
        elif retry_agent == "FIN":
            response = retry
        else:
            # Fallback de seguridad: el supervisor insiste en un agente no disponible
            pending = _next_pending_agent(state, agent_call_counts)
            if pending is not None:
                response.next_agent = pending
                agent_call_counts[pending] = agent_call_counts.get(pending, 0) + 1
                response.feedback = (
                    f"Completa tu entrega basándote en la investigación y planes anteriores. "
                    f"No repitas trabajo ya realizado."
                )
                logger.info(
                    "Agente %s sin cupo o ya aprobado. Redirigiendo a %s.",
                    agent_name, pending,
                )
            else:
                response.next_agent = "FIN"
                response.feedback = "Todos los agentes han entregado su trabajo o agotaron su cupo. La campaña está completa."
                logger.info("Todos los agentes han entregado. Finalizando campaña.")
    elif agent_name != "FIN":
        agent_call_counts[agent_name] = agent_call_counts.get(agent_name, 0) + 1

    completion_reason = "completed" if response.next_agent == "FIN" else "in_progress"

    # Registrar mensaje en el historial del flujo
    log_message = AIMessage(
        content=f"[CMO]: Delegando a {response.next_agent.upper()}. Instrucciones: {response.feedback}"
    )
    
    return {
        "next_agent": response.next_agent,
        "supervisor_feedback": response.feedback,
        "completion_reason": completion_reason,
        "agent_call_counts": agent_call_counts,
        "messages": [log_message]
    }

def researcher_node(state: MarketingState):
    """
    Nodo Investigador de Mercado.
    Utiliza un agente ReAct dinámico con herramientas de LightPanda para buscar competidores y dolores.
    """
    feedback = state.get("supervisor_feedback") or "Comienza la investigación básica de mercado."
    system_prompt = RESEARCHER_SYSTEM_PROMPT.format(supervisor_feedback=feedback)
    
    # Crear agente ReAct dinámicamente con acceso a herramientas
    agent = create_react_agent(
        model=get_researcher_llm(),
        tools=[search_web_lightpanda, scrape_website_lightpanda],
        prompt=system_prompt
    )
    
    # Invocar al agente pasándole el producto
    inputs = {
        "messages": [
            HumanMessage(content=f"Investiga el mercado para el siguiente producto/servicio: {state['product_description']}")
        ]
    }
    result = agent.invoke(inputs)
    
    # Extraer el último mensaje que contiene la respuesta sintetizada final
    last_msg = result["messages"][-1]
    research = last_msg.content

    # Fallback: si el scraping no obtuvo datos suficientes, generar un reporte
    # a partir del conocimiento del modelo sin herramientas
    if len(research) < MIN_RESEARCH_LENGTH or "No disponible" in research:
        fallback_llm = get_researcher_llm()
        fallback_result = fallback_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"No se pudieron obtener datos de scraping web para el producto: {state['product_description']}. "
                "Genera un reporte de investigación de mercado completo basado en tu conocimiento, "
                "incluyendo al menos 2-3 competidores, dolores del cliente, precios sugeridos y fuentes."
            ))
        ])
        research = fallback_result.content

    log_message = AIMessage(content="[Investigador]: He finalizado el reporte de investigación de mercado y competidores.")
    
    return {
        "market_research": research,
        "messages": [log_message]
    }

def copywriter_node(state: MarketingState):
    """
    Nodo Copywriter Creativo.
    Redacta piezas de marketing persuasivas (anuncios, correos, landing) estructuradas en JSON.
    """
    feedback = state.get("supervisor_feedback") or "Crea los borradores iniciales de copy persuasivo."
    
    prompt = COPYWRITER_SYSTEM_PROMPT.format(
        product_description=state["product_description"],
        market_research=state.get("market_research") or "No disponible.",
        seo_channels_plan=state.get("seo_channels_plan") or "No disponible.",
        supervisor_feedback=feedback
    )
    
    # Obtener el LLM del copywriter y enlazar salida estructurada
    llm = get_copywriter_llm()
    structured_llm = llm.with_structured_output(CopywriterOutput)
    
    # Invocar al copywriter
    response = structured_llm.invoke([SystemMessage(content=prompt)])
    
    drafts = {
        "anuncios": response.anuncios,
        "emails": response.emails,
        "landing": response.landing
    }
    
    log_message = AIMessage(content="[Copywriter]: He redactado los anuncios, correos y la estructura de la landing page.")
    
    return {
        "copywriting_drafts": drafts,
        "messages": [log_message]
    }

def strategist_node(state: MarketingState):
    """
    Nodo Estratega de Canales/SEO.
    Diseña la distribución y plan de palabras clave y lo guarda en formato Markdown.
    """
    feedback = state.get("supervisor_feedback") or "Diseña la estrategia inicial de SEO y canales."
    
    prompt = STRATEGIST_SYSTEM_PROMPT.format(
        product_description=state["product_description"],
        market_research=state.get("market_research") or "No disponible.",
        supervisor_feedback=feedback
    )
    
    # Invocar al estratega (salida estándar en Markdown)
    llm = get_strategist_llm()
    response = llm.invoke([SystemMessage(content=prompt)])
    
    log_message = AIMessage(content="[Estratega]: He diseñado el plan de canales y la estrategia SEO.")
    
    return {
        "seo_channels_plan": response.content,
        "messages": [log_message]
    }
