from types import SimpleNamespace

from agente_ventas.nodes import supervisor_node


class DummyStructuredLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def invoke(self, messages):
        return self.responses.pop(0)


class DummyLLM:
    def __init__(self, responses):
        self.responses = [
            SimpleNamespace(next_agent=agent, feedback=feedback)
            for agent, feedback in responses
        ]

    def with_structured_output(self, schema):
        return DummyStructuredLLM(self.responses)


def make_state(agent_call_counts, market_research="", seo_channels_plan="", copywriting_drafts=None):
    return {
        "product_description": "Producto de prueba",
        "messages": [],
        "market_research": market_research,
        "seo_channels_plan": seo_channels_plan,
        "copywriting_drafts": copywriting_drafts or {},
        "supervisor_feedback": "",
        "next_agent": "",
        "completion_reason": "",
        "agent_call_counts": agent_call_counts,
    }


LONG_RESEARCH = "Reporte extenso de investigación de mercado y competidores " * 5


def test_supervisor_increments_counter_when_delegating(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Continúa con la investigación.")]),
    )

    state = make_state({"investigador": 1})

    result = supervisor_node(state)

    assert result["next_agent"] == "investigador"
    assert result["completion_reason"] == "in_progress"
    assert result["agent_call_counts"] == {"investigador": 2}


def test_supervisor_redirects_when_agent_exhausted(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Genérico."), ("investigador", "Genérico.")]),
    )

    state = make_state({"investigador": 3, "estratega": 0, "copywriter": 0})

    result = supervisor_node(state)

    assert result["next_agent"] == "estratega"
    assert result["completion_reason"] == "in_progress"
    assert result["agent_call_counts"] == {"investigador": 3, "estratega": 1, "copywriter": 0}


def test_supervisor_finishes_when_all_agents_exhausted(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Genérico."), ("investigador", "Genérico.")]),
    )

    state = make_state({"investigador": 3, "estratega": 3, "copywriter": 3})

    result = supervisor_node(state)

    assert result["next_agent"] == "FIN"
    assert result["completion_reason"] == "completed"


def test_supervisor_skips_approved_agent_with_generic_feedback(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Continúa con la investigación."), ("investigador", "Continúa.")]),
    )

    state = make_state({"investigador": 1}, market_research=LONG_RESEARCH)

    result = supervisor_node(state)

    assert result["next_agent"] == "estratega"
    assert result["agent_call_counts"] == {"investigador": 1, "estratega": 1}


def test_supervisor_allows_revision_when_feedback_asks_changes(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Corregir la sección de competidores.")]),
    )

    state = make_state({"investigador": 1}, market_research=LONG_RESEARCH)

    result = supervisor_node(state)

    assert result["next_agent"] == "investigador"
    assert result["agent_call_counts"] == {"investigador": 2}


def test_supervisor_finishes_when_all_agents_delivered(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Continúa."), ("investigador", "Continúa.")]),
    )

    state = make_state(
        {"investigador": 1, "estratega": 1, "copywriter": 1},
        market_research=LONG_RESEARCH,
        seo_channels_plan="Plan extenso de SEO y canales de distribución " * 5,
        copywriting_drafts={"anuncios": "texto", "emails": "texto", "landing": "texto"},
    )

    result = supervisor_node(state)

    assert result["next_agent"] == "FIN"
    assert result["completion_reason"] == "completed"
    assert result["agent_call_counts"] == {"investigador": 1, "estratega": 1, "copywriter": 1}


def test_supervisor_reconsults_and_uses_retry_decision(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([
            ("investigador", "Sigue investigando."),
            ("copywriter", "Redacta anuncios con foco en los dolores del reporte."),
        ]),
    )

    state = make_state(
        {"investigador": 3, "estratega": 0, "copywriter": 0},
        market_research=LONG_RESEARCH,
    )

    result = supervisor_node(state)

    assert result["next_agent"] == "copywriter"
    assert result["supervisor_feedback"] == "Redacta anuncios con foco en los dolores del reporte."
    assert result["agent_call_counts"] == {"investigador": 3, "estratega": 0, "copywriter": 1}


def test_supervisor_reconsults_and_uses_retry_fin(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("investigador", "Sigue investigando."), ("FIN", "Campaña completa.")]),
    )

    state = make_state({"investigador": 3, "estratega": 0, "copywriter": 0})

    result = supervisor_node(state)

    assert result["next_agent"] == "FIN"
    assert result["completion_reason"] == "completed"


def test_supervisor_gate_blocks_copywriter_with_empty_research(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("copywriter", "Redacta anuncios.")]),
    )

    state = make_state({"investigador": 0}, market_research="")

    result = supervisor_node(state)

    assert result["next_agent"] == "investigador"
    assert "insuficiente" in result["supervisor_feedback"]


def test_supervisor_gate_allows_copywriter_with_sufficient_research(monkeypatch):
    monkeypatch.setattr(
        "agente_ventas.nodes.get_supervisor_llm",
        lambda: DummyLLM([("copywriter", "Redacta anuncios.")]),
    )

    state = make_state({"investigador": 1}, market_research=LONG_RESEARCH)

    result = supervisor_node(state)

    assert result["next_agent"] == "copywriter"
    assert result["agent_call_counts"] == {"investigador": 1, "copywriter": 1}
