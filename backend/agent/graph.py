from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

try:
    from agent.state import InterviewState
    from agent.nodes import (
        intro_node,
        p1_approach_node,
        p1_coding_and_verify_node,
        p1_complexity_and_adaptive_select_node,
        p2_approach_and_coding_node,
        p2_coding_and_verify_node,
        p2_followup_node,
        wrapup_node
    )
    from agent.cv_grill_nodes import (
        cv_intro_node,
        cv_acknowledge_pick_node,
        cv_project_deepdive_node,
        cv_next_topic_node,
        cv_wrapup_node
    )
except (ImportError, ModuleNotFoundError):
    from .state import InterviewState
    from .nodes import (
        intro_node,
        p1_approach_node,
        p1_coding_and_verify_node,
        p1_complexity_and_adaptive_select_node,
        p2_approach_and_coding_node,
        p2_coding_and_verify_node,
        p2_followup_node,
        wrapup_node
    )
    from .cv_grill_nodes import (
        cv_intro_node,
        cv_acknowledge_pick_node,
        cv_project_deepdive_node,
        cv_next_topic_node,
        cv_wrapup_node
    )

def build_interviewer_graph():
    """
    Builds and compiles the stateful LangGraph Interviewer Agent.
    """
    workflow = StateGraph(InterviewState)

    # 1. Add Nodes
    workflow.add_node("intro", intro_node)
    workflow.add_node("p1_approach", p1_approach_node)
    workflow.add_node("p1_coding", p1_coding_and_verify_node)
    workflow.add_node("p1_complexity", p1_complexity_and_adaptive_select_node)
    workflow.add_node("p2_approach", p2_approach_and_coding_node)
    workflow.add_node("p2_coding", p2_coding_and_verify_node)
    workflow.add_node("p2_followup", p2_followup_node)
    workflow.add_node("wrapup", wrapup_node)

    # CV Grilling Nodes
    workflow.add_node("cv_intro", cv_intro_node)
    workflow.add_node("cv_acknowledge_pick", cv_acknowledge_pick_node)
    workflow.add_node("cv_project_deepdive", cv_project_deepdive_node)
    workflow.add_node("cv_next_topic", cv_next_topic_node)
    workflow.add_node("cv_wrapup", cv_wrapup_node)

    # 2. Add Edges & Conditional Routing
    workflow.set_entry_point("intro")
    
    workflow.add_edge("intro", "p1_approach")
    workflow.add_edge("p1_approach", "p1_coding")
    workflow.add_edge("p1_coding", "p1_complexity")
    workflow.add_edge("p1_complexity", "p2_approach")
    workflow.add_edge("p2_approach", "p2_coding")
    workflow.add_edge("p2_coding", "p2_followup")
    workflow.add_edge("p2_followup", "wrapup")
    workflow.add_edge("wrapup", END)

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app

# Singleton compiled graph instance
interviewer_agent = build_interviewer_graph()

async def execute_agent_turn(state: InterviewState, action_type: str = "text") -> dict:
    """
    Executes one turn of the agent graph depending on current phase and interview track.
    """
    track = state.get("track", "medium")
    phase = state.get("current_phase", "Intro")

    # CV Grilling Track Routing
    if track == "cv_grill" or phase.startswith("CV"):
        if phase in ("Intro", "CV Intro"):
            return await cv_intro_node(state)
        elif phase == "CV Awaiting Pick":
            return await cv_acknowledge_pick_node(state)
        elif phase == "CV Project Deep Dive":
            return await cv_project_deepdive_node(state)
        elif phase == "CV Next Topic":
            return await cv_next_topic_node(state)
        elif phase in ("CV Wrap-up", "Wrap-up", "Completed"):
            return await cv_wrapup_node(state)
        else:
            return await cv_project_deepdive_node(state)

    # Standard DSA Problem Track Routing
    if phase == "Intro":
        return await intro_node(state)
    elif phase == "P1 Approach":
        return await p1_approach_node(state)
    elif phase == "P1 Coding":
        return await p1_coding_and_verify_node(state)
    elif phase == "P1 Complexity":
        return await p1_complexity_and_adaptive_select_node(state)
    elif phase == "P2 Approach":
        return await p2_approach_and_coding_node(state)
    elif phase == "P2 Coding":
        return await p2_coding_and_verify_node(state)
    elif phase == "P2 Followup":
        return await p2_followup_node(state)
    elif phase == "Wrap-up":
        return await wrapup_node(state)
    else:
        return await intro_node(state)

