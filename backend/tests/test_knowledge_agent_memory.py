from langchain_core.messages import AIMessage

from app.services.knowledge_agent import KnowledgeAgentService


class DummyModel:
    def __init__(self):
        self.calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(content=f"answer-{self.calls}")


def test_query_persists_conversation_memory():
    service = KnowledgeAgentService()
    service.llm_service.primary_model = DummyModel()
    service.graph = service._build_graph()

    first = service.query("first question", [], "conv-123")
    second = service.query("follow-up question", [], "conv-123")

    assert first["conversation_id"] == "conv-123"
    assert second["conversation_id"] == "conv-123"

    state = service.graph.get_state(config={"configurable": {"thread_id": "conv-123"}})
    assert state is not None
    assert state.values.get("conversation_id") == "conv-123"
    assert len(state.values.get("messages", [])) >= 2
