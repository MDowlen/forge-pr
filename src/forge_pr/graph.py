from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .models import WorkflowState
from .nodes import context_node, deterministic_node, gate_node, quality_node, test_plan_node


def build_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("context", context_node)
    graph.add_node("deterministic", deterministic_node)
    graph.add_node("quality", quality_node)
    graph.add_node("test_plan", test_plan_node)
    graph.add_node("gate", gate_node)

    graph.add_edge(START, "context")
    graph.add_edge("context", "deterministic")
    graph.add_edge("deterministic", "quality")
    graph.add_edge("quality", "test_plan")
    graph.add_edge("test_plan", "gate")
    graph.add_edge("gate", END)
    return graph.compile()
