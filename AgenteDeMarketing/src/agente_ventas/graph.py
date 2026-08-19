"""
LangGraph Workflow Assembly and Compilation.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agente_ventas.state import MarketingState
from agente_ventas.nodes import (
    supervisor_node,
    researcher_node,
    copywriter_node,
    strategist_node,
)

def route_supervisor(state: MarketingState):
    """
    Ruteador condicional para las decisiones del Supervisor.
    """
    next_agent = state.get("next_agent")

    if next_agent == "investigador":
        return "investigador"
    elif next_agent == "copywriter":
        return "copywriter"
    elif next_agent == "estratega":
        return "estratega"
    else:
        # Cualquier otro valor o "FIN" terminará la ejecución
        return END

# ===== GRAPH CONSTRUCTION =====

workflow = StateGraph(MarketingState)

# Registrar los nodos
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("investigador", researcher_node)
workflow.add_node("copywriter", copywriter_node)
workflow.add_node("estratega", strategist_node)

# El punto de entrada principal es siempre el Supervisor (CMO)
workflow.add_edge(START, "supervisor")

# Añadir las aristas condicionales de ruteo del Supervisor
workflow.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "investigador": "investigador",
        "copywriter": "copywriter",
        "estratega": "estratega",
        "__end__": END
    }
)

# Los agentes especialistas siempre reportan de vuelta al Supervisor al terminar
workflow.add_edge("investigador", "supervisor")
workflow.add_edge("copywriter", "supervisor")
workflow.add_edge("estratega", "supervisor")

# Compilar el grafo con persistencia de memoria local en memoria (MemorySaver)
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)
