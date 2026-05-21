# 에이전트 아키텍처 패턴
import operator
from typing import Annotated, List, TypedDict, Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

# Sequential Agent
# 순차적 에이전트(Sequential Agent)는 여러 단계에 걸쳐 내부 추론을 수행. 스크래치패드(scratchpad)라는 방식으로 진행. 별도의 외부 도구를 전혀 사용하지 않음.
# 순수한 분석과 연역적 추론만으로도 충분한 상황에 주로 사용.

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class State(TypedDict):
    question: str
    steps: Annotated[List[str], operator.add]
    answer: str

def plan_node(state: State) -> dict:
    sys = (
        "당신은 신중한 계획자입니다. 사용자의 질문을 2-4개의 간결한 단계로 나누세요. "
        "문제를 해결하지는 마세요. 번호가 매겨진 단계 목록만 반환하고, 추가 텍스트는 작성하지 마세요."
    )
    messages = [("system", sys), ("user", state["question"])]
    resp = llm.invoke(messages)
    raw = resp.content
    steps = []
    for line in str(raw).splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.lstrip("-• ").split(". ", 1)[-1] if ". " in line[:4] else line.lstrip("-• ")
        steps.append(line)
    return {"steps": steps}

def solve_node(state: State) -> dict:
    """계획된 단계를 사용하여 최종 답변만 도출합니다."""
    sys = (
        "제공된 단계를 사용하여 문제를 해결하세요. "
        "최종 답변만 반환하고, 추론 과정은 포함하지 마세요."
    )
    messages = [
        ("system", sys),
        ("user", f"질문: {state['question']}\\\\n단계: {state['steps']}"),
    ]
    resp = llm.invoke(messages)
    return {"answer": str(resp.content).strip()}

#  Wire up the graph
graph = StateGraph(State)
graph.add_node("plan", plan_node)
graph.add_node("solve", solve_node)

graph.add_edge(START, "plan")
graph.add_edge("plan", "solve")
graph.add_edge("solve", END)

cot_graph = graph.compile()

state = {
    "question": "강의 동영상이 120개이고 하루에 15개를 본다면, 완강하는 데 며칠이 걸릴까요?",
    "steps": [],
    "answer": ""
}
out = cot_graph.invoke(state)
print("최종 답변:", out["answer"])


# Custom Agent
# 커스텀 에이전트(Custom Agent)는 유연성을 제공. 사용자는 전체적인 로직과 라우팅을 직접 설계할 수 있음. 또한 시스템을 구성하는 개별 노드까지 스스로 정의. 사용자의 요구에 맞춰 자유롭게 맞춤형 제어가 가능.
class CustomState(TypedDict):
    input: str
    task: Literal["math", "capitalize", "count"]
    result: str

def route(state: CustomState) -> str:
    """Deterministic router based on a simple protocol in the input."""
    text = state["input"].strip().lower()
    if text.startswith("math:"):
        return "math"
    if text.startswith("capitalize:"):
        return "capitalize"
    if text.startswith("count:"):
        return "count"
    return "count"

def do_math(state: CustomState) -> dict:
    expr = state["input"].split(":", 1)[-1].strip()
    allowed = set("0123456789+-*/(). ")
    if any(c not in allowed for c in expr):
        return {"result": "Error: unsupported characters in math expression."}
    try:
        res = eval(expr, {"__builtins__": {}})
    except Exception as e:
        res = f"Error: {e}"
    return {"result": str(res)}

def do_capitalize(state: CustomState) -> dict:
    text = state["input"].split(":", 1)[-1].strip()
    return {"result": text.upper()}

def do_count(state: CustomState) -> dict:
    text = state["input"].split(":", 1)[-1].strip()
    tokens = [t for t in text.split() if t]
    return {"result": f"words={len(tokens)} chars={len(text)}"}

graph = StateGraph(CustomState)
graph.add_node("math", do_math)
graph.add_node("capitalize", do_capitalize)
graph.add_node("count", do_count)

graph.add_conditional_edges(
    START,
    route,
    {
        "math": "math",
        "capitalize": "capitalize",
        "count": "count",
    },
)
graph.add_edge("math", END)
graph.add_edge("capitalize", END)
graph.add_edge("count", END)

custom_agent = graph.compile(debug=True)

for user_input in [
    "math: (16 + 3) * 2 + 5",
    "capitalize: hello world from AI agent",
    "count: 여기에 몇 개의 단어가 있나요?",
]:
    out = custom_agent.invoke({"input": user_input, "task": "count", "result": ""})
    print(f"입력: {user_input}\\n결과: {out['result']}\\n---")


# Supervisor
# 슈퍼바이저(Supervisor) 패턴은 중앙 제어형 에이전트가 전체 작업을 관리합. 상위 에이전트가 문제를 분석한 뒤 이를 여러 하위 노드에 나누어 배정. 각 하위 노드가 작업을 마치면 그 결과를 다시 취합하고 검토.복잡한 작업을 나누어 병렬로 처리하거나 중앙 통제가 필요할 때 유용.
class SupervisorState(TypedDict):
    """여러 에이전트가 있는 슈퍼바이저 패턴의 상태."""
    topic: str
    messages: Annotated[List[str], operator.add]
    next_agent: str
    final_answer: str


def researcher_agent(state: SupervisorState) -> dict:
    """연구자 에이전트는 주제에 대한 정보를 수집합니다."""
    sys = (
        "당신은 연구자입니다. 주어진 주제에 대한 핵심 사실과 정보를 "
        "수집하는 것이 당신의 임무입니다. 2-3개의 핵심 포인트를 제공하세요. 간결하게 작성하세요."
    )
    messages_for_llm = [
        ("system", sys),
        ("user", f"다음 주제를 조사하세요: {state['topic']}")
    ]
    resp = llm.invoke(messages_for_llm)
    research_msg = f"연구자: {resp.content}"
    return {"messages": [research_msg]}


def expert_agent(state: SupervisorState) -> dict:
    """전문가 에이전트는 연구를 기반으로 분석하고 통찰력을 제공합니다."""
    sys = (
        "당신은 전문 분석가입니다. 제공된 연구를 검토하고 "
        "전문가 분석과 결론을 제공하세요. 구체적이고 통찰력 있게 작성하세요."
    )
    # 이전 메시지에서 컨텍스트 가져오기
    context = "\n".join(state["messages"])
    messages_for_llm = [
        ("system", sys),
        ("user", f"주제: {state['topic']}\n\n이전 조사 내용:\n{context}\n\n전문가 분석을 제공하세요.")
    ]
    resp = llm.invoke(messages_for_llm)
    expert_msg = f"전문가: {resp.content}"
    return {"messages": [expert_msg]}


def supervisor_agent(state: SupervisorState) -> dict:
    """슈퍼바이저는 다음에 어떤 에이전트가 활동할지 또는 토론을 종료할지 결정합니다."""
    sys = (
        "당신은 연구자와 전문가 간의 조사 토론을 관리하는 슈퍼바이저입니다. "
        "지금까지의 대화를 바탕으로 다음에 무엇을 해야 할지 결정하세요:\n"
        "- 초기 조사나 추가 정보가 필요하면 'researcher'를 반환하세요\n"
        "- 조사가 완료되고 전문가 분석이 필요하면 'expert'를 반환하세요\n"
        "- 조사와 전문가 분석이 모두 완료되면 'end'를 반환하세요\n\n"
        "단 하나의 단어만 응답하세요: researcher, expert, 또는 end"
    )

    context = "\n".join(state["messages"]) if state["messages"] else "아직 토론이 없습니다"
    messages_for_llm = [
        ("system", sys),
        ("user", f"주제: {state['topic']}\n\n대화 내용:\n{context}\n\n다음은 무엇인가요?")
    ]
    resp = llm.invoke(messages_for_llm)
    next_step = resp.content.strip().lower()

    # 유효한 응답인지 확인
    if next_step not in ["researcher", "expert", "end"]:
        next_step = "end"

    return {"next_agent": next_step}


def finalize_answer(state: SupervisorState) -> dict:
    """토론에서 최종 답변을 작성합니다."""
    sys = (
        "조사 토론을 명확하고 간결한 최종 답변으로 요약하세요. "
        "핵심 발견 사항과 전문가 통찰력을 포함하세요."
    )
    context = "\n".join(state["messages"])
    messages_for_llm = [
        ("system", sys),
        ("user", f"주제: {state['topic']}\n\n토론 내용:\n{context}\n\n최종 요약을 제공하세요:")
    ]
    resp = llm.invoke(messages_for_llm)
    return {"final_answer": resp.content}


def route_supervisor(state: SupervisorState) -> str:
    """슈퍼바이저의 결정에 따라 라우팅합니다."""
    next_agent = state.get("next_agent", "researcher")
    if next_agent == "end":
        return "finalize"
    return next_agent

supervisor_graph = StateGraph(SupervisorState)

supervisor_graph.add_node("supervisor", supervisor_agent)
supervisor_graph.add_node("researcher", researcher_agent)
supervisor_graph.add_node("expert", expert_agent)
supervisor_graph.add_node("finalize", finalize_answer)

supervisor_graph.add_edge(START, "supervisor")

supervisor_graph.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "researcher": "researcher",
        "expert": "expert",
        "finalize": "finalize"
    }
)

supervisor_graph.add_edge("researcher", "supervisor")
supervisor_graph.add_edge("expert", "supervisor")

supervisor_graph.add_edge("finalize", END)

supervisor_agent_graph = supervisor_graph.compile(debug=True)

topic = "AI 에이전트를 구축하는 데 LangGraph를 사용하는 주요 이점은 무엇인가요?"

initial_state = {
    "topic": topic,
    "messages": [],
    "next_agent": "",
    "final_answer": ""
}

result = supervisor_agent_graph.invoke(initial_state)

print(f"주제: {topic}\n")
print("=" * 80)
print("\n토론 내용:")
print("-" * 80)
for msg in result["messages"]:
    print(f"\n{msg}\n")
print("=" * 80)
print(f"\n최종 답변:\n{result['final_answer']}")
