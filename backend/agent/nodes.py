import os
import json
import time
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from agent.state import InterviewState
    from agent.problem_engine import select_adaptive_problem, generate_novel_problem_with_ai
    from problems_db import PROBLEMS, get_problem_by_id
except (ImportError, ModuleNotFoundError):
    from .state import InterviewState
    from .problem_engine import select_adaptive_problem, generate_novel_problem_with_ai
    from ..problems_db import PROBLEMS, get_problem_by_id

def get_llm(model: str = "gemini-3.1-flash-lite", temperature: float = 0.6):
    api_key = os.getenv("GEMINI_API_KEY")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature
    )

def extract_text(content: Any) -> str:
    """Safely extracts clean string text from LangChain message content."""
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif hasattr(item, "text"):
                parts.append(item.text)
        return " ".join(parts).strip()
    return str(content).strip()

def build_langchain_messages(system_prompt: str, messages: list, default_user_text: str = "Hello."):
    """Builds a valid list of LangChain messages ensuring at least one HumanMessage is present."""
    langchain_messages = [SystemMessage(content=system_prompt)]
    has_human = False
    for msg in messages[-6:]:
        if msg.get("role") == "user":
            langchain_messages.append(HumanMessage(content=msg.get("content", "")))
            has_human = True
        elif msg.get("role") in ["assistant", "model"]:
            langchain_messages.append(AIMessage(content=msg.get("content", "")))

    if not has_human:
        langchain_messages.append(HumanMessage(content=default_user_text))

    return langchain_messages

async def intro_node(state: InterviewState) -> Dict[str, Any]:
    """Handles warm candidate greeting and natural background/project discussion."""
    llm = get_llm()
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    track_name = state.get("track_name", "General SDE")
    resume_summary = state.get("resume_summary", "Software Engineering")
    messages = state.get("messages", [])
    q1 = state.get("current_problem") or PROBLEMS["two_sum"]
    lang = state.get("language", "python")

    ai_turns = [m for m in messages if m.get("role") in ["assistant", "model"]]
    
    # Turn 1: Opening greeting
    if len(ai_turns) == 0:
        system_prompt = f"""You are {interviewer_name}, an expert Senior Technical Interviewer conducting a live DSA interview for the {track_name} track.
Candidate: {candidate_name}
Candidate Background: {resume_summary}

Your Goal:
Greet {candidate_name} warmly and ask 1 brief question asking them to introduce themselves and discuss their background or a recent technical project.

Keep your response SHORT (1-2 sentences), warm, and conversational. Do NOT present any coding problems yet.
"""
        langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text=f"Hi {interviewer_name}, I am {candidate_name} and I am ready to start.")
        response = await llm.ainvoke(langchain_messages)
        spoken = extract_text(response.content)

        return {
            "spoken_response": spoken,
            "current_phase": "Intro",
            "editor_unlocked": False
        }
    else:
        # Subsequent turns in Intro: Let LLM dynamically converse about the project or transition to coding
        system_prompt = f"""You are {interviewer_name}, an expert Senior Technical Interviewer conducting a live DSA interview for the {track_name} track.
Candidate: {candidate_name}
Candidate Resume: {resume_summary}
First Problem: {q1['title']}

You are in the Introduction & Background phase of the interview.

Assess the candidate's last message:
1. If candidate gave an initial introduction and you want to ask 1 interesting technical follow-up about their project (e.g. asking about architecture, trade-offs, or a challenge they solved):
   - Ask the follow-up question.
   - Set "ready_for_coding": false (DO NOT mention any coding problem yet, wait for candidate to answer).
2. If candidate answered your project follow-up question OR the candidate explicitly says they are ready for the coding problem OR we have had enough discussion (ai_turns >= 2):
   - Acknowledge their project explanation warmly in 1 sentence.
   - Then announce the first coding problem ({q1['title']}) and invite them to share their initial thoughts:
     e.g., "That's a great architectural choice! Let's now take a look at our first problem on the left: {q1['title']}. Could you walk me through your initial thoughts and approach for solving this?"
   - Set "ready_for_coding": true.

Output valid JSON only:
{{
    "ai_response": "1-2 sentences spoken response",
    "ready_for_coding": true | false
}}
"""
        langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="I am ready to proceed.")
        
        try:
            response = await llm.ainvoke(langchain_messages)
            clean = extract_text(response.content)
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            parsed = json.loads(clean.strip())

            spoken = parsed.get("ai_response", "Let's take a look at our first problem.")
            ready = parsed.get("ready_for_coding", len(ai_turns) >= 2)

            if ready:
                return {
                    "spoken_response": spoken,
                    "current_phase": "P1 Approach",
                    "active_problem_id": q1["id"],
                    "current_problem": q1,
                    "problem_html": q1["html"],
                    "starter_code": q1["starter_code"].get(lang, q1["starter_code"]["python"]),
                    "editor_unlocked": True
                }
            else:
                return {
                    "spoken_response": spoken,
                    "current_phase": "Intro",
                    "editor_unlocked": False
                }
        except Exception:
            return {
                "spoken_response": f"Thanks for sharing that background! Let's take a look at the first problem on the left: {q1['title']}. Could you walk me through your initial thoughts and approach?",
                "current_phase": "P1 Approach",
                "active_problem_id": q1["id"],
                "current_problem": q1,
                "problem_html": q1["html"],
                "starter_code": q1["starter_code"].get(lang, q1["starter_code"]["python"]),
                "editor_unlocked": True
            }

async def p1_approach_node(state: InterviewState) -> Dict[str, Any]:
    """Analyzes candidate's verbal logic, checks data structure choices, and gives directional hints if needed."""
    llm = get_llm()
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    q1 = state.get("current_problem") or PROBLEMS["two_sum"]
    messages = state.get("messages", [])
    hints_history = state.get("hints_history", [])

    system_prompt = f"""You are {interviewer_name}, Senior Technical Interviewer.
Candidate: {candidate_name}
Problem: {q1['title']}
Problem Category: {q1.get('category', 'Algorithms')}

Candidate is currently discussing their approach before coding.

Assess the candidate's last message:
1. WRONG DIRECTION / WRONG DATA STRUCTURE:
   - If candidate proposes an unsuitable data structure (e.g. nested linear scans where Hash Map is required, or recursion where DP/iteration is needed), provide a gentle Socratic hint to steer them in the right direction without giving away the complete answer.
2. BRUTE FORCE:
   - If candidate explains a working brute force (O(N^2)), acknowledge it and ask: "That works, but can we optimize the time complexity?"
3. OPTIMAL / SOUND APPROACH:
   - If candidate explains an optimal or solid approach, praise them enthusiastically and EXPLICITLY TELL THEM TO WRITE CODE:
     "That sounds like a great approach! Please go ahead and write the code in the editor."

Output valid JSON only:
{{
    "classification": "wrong_ds" | "brute_force" | "optimal",
    "ai_response": "1-2 sentences spoken response",
    "advance_to_coding": true | false
}}
"""
    langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="Here is my approach for solving this.")

    try:
        response = await llm.ainvoke(langchain_messages)
        clean = extract_text(response.content)
        if clean.startswith("```json"): clean = clean[7:]
        if clean.startswith("```"): clean = clean[3:]
        if clean.endswith("```"): clean = clean[:-3]
        parsed = json.loads(clean.strip())
        
        spoken = parsed.get("ai_response", "Please explain your approach.")
        classification = parsed.get("classification", "optimal")
        advance = parsed.get("advance_to_coding", False)
        
        if classification == "wrong_ds":
            hints_history.append({
                "problem_id": q1["id"],
                "type": "wrong_ds",
                "text": spoken,
                "level": 1
            })
            
        next_phase = "P1 Coding" if advance else "P1 Approach"
        return {
            "spoken_response": spoken,
            "current_phase": next_phase,
            "candidate_approach_optimality": classification,
            "hints_history": hints_history,
            "editor_unlocked": True
        }
    except Exception as e:
        print(f"Error in p1_approach_node: {e}")
        return {
            "spoken_response": "That sounds like a solid plan! Please go ahead and write the code in the editor.",
            "current_phase": "P1 Coding",
            "editor_unlocked": True
        }

async def p1_coding_and_verify_node(state: InterviewState) -> Dict[str, Any]:
    """Handles code submissions, test verification, and probes Time & Space complexity."""
    llm = get_llm()
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    q1 = state.get("current_problem") or PROBLEMS["two_sum"]
    test_results = state.get("test_results") or {}
    editor_code = state.get("editor_code", "")
    language = state.get("language", "python")
    messages = state.get("messages", [])

    all_passed = test_results.get("all_passed", False)
    total_passed = test_results.get("total_passed", 0)
    total_tests = test_results.get("total_tests", 0)

    system_prompt = f"""You are {interviewer_name}, Senior Technical Interviewer.
Candidate: {candidate_name}
Problem: {q1['title']}
Code Language: {language}
Test Cases: {total_passed} out of {total_tests} passed. All passed: {all_passed}.

Candidate's Code:
```{language}
{editor_code}
```

Instructions:
- If all test cases passed or code is submitted:
  * Acknowledge the implementation.
  * EXPLICITLY ASK for Time Complexity and Space Complexity:
    "Great job on the implementation! What is the time complexity and space complexity of your solution?"
  * Set "next_phase": "P1 Complexity".
- If tests failed:
  * Give a brief hint about the failing case or bug.
  * Set "next_phase": "P1 Coding".

Output valid JSON only:
{{
    "ai_response": "1-2 sentences spoken response",
    "next_phase": "P1 Complexity" | "P1 Coding"
}}
"""
    langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="I have submitted my code.")

    try:
        response = await llm.ainvoke(langchain_messages)
        clean = extract_text(response.content)
        if clean.startswith("```json"): clean = clean[7:]
        if clean.startswith("```"): clean = clean[3:]
        if clean.endswith("```"): clean = clean[:-3]
        parsed = json.loads(clean.strip())
        
        spoken = parsed.get("ai_response", "Great job! What is the time and space complexity?")
        next_phase = parsed.get("next_phase", "P1 Complexity")
        
        return {
            "spoken_response": spoken,
            "current_phase": next_phase,
            "q1_stats": {"passed": total_passed, "total": total_tests, "attempts": 1},
            "editor_unlocked": True
        }
    except Exception as e:
        return {
            "spoken_response": "Great job on the implementation! What is the time complexity and space complexity of your solution?",
            "current_phase": "P1 Complexity",
            "editor_unlocked": True
        }

async def p1_complexity_and_adaptive_select_node(state: InterviewState) -> Dict[str, Any]:
    """Validates candidate's Big-O analysis and dynamically selects adaptive Question 2."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    q1 = state.get("current_problem") or PROBLEMS["two_sum"]
    track = state.get("track", "general")
    q1_stats = state.get("q1_stats") or {"passed": 2, "total": 2}
    hints_history = state.get("hints_history") or []
    lang = state.get("language", "python")

    # Select Adaptive Problem 2
    q2 = select_adaptive_problem(
        track=track,
        q1_stats=q1_stats,
        hints_used=len(hints_history),
        exclude_ids=[q1["id"]]
    )

    spoken = f"Spot on with the complexity analysis! Let's move to our second problem on the left: {q2['title']} ({q2.get('difficulty', 'Medium')}). Could you share your approach for this one?"

    problems_completed = state.get("problems_completed", [])
    problems_completed.append(q1)

    return {
        "spoken_response": spoken,
        "current_phase": "P2 Approach",
        "current_problem": q2,
        "active_problem_id": q2["id"],
        "problem_html": q2["html"],
        "starter_code": q2["starter_code"].get(lang, q2["starter_code"]["python"]),
        "problems_completed": problems_completed,
        "editor_unlocked": True
    }

async def p2_approach_and_coding_node(state: InterviewState) -> Dict[str, Any]:
    """Guides Q2 approach and invites code implementation."""
    llm = get_llm()
    q2 = state.get("current_problem") or PROBLEMS["merge_intervals"]
    messages = state.get("messages", [])

    system_prompt = f"""You are {interviewer_name}, Senior Technical Interviewer.
Candidate is discussing Question 2: {q2['title']} ({q2.get('category', 'Algorithms')}).

If approach is viable/optimal:
- Praise them enthusiastically and EXPLICITLY TELL THEM TO CODE:
  "Awesome logic! Please go ahead and write the implementation in the editor."
  (advance_to_coding: true)
If approach needs adjustment:
- Offer a gentle Socratic hint (advance_to_coding: false).

Output JSON only:
{{
    "ai_response": "1-2 sentences spoken response",
    "advance_to_coding": true | false
}}
"""
    langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="Here is my approach for Question 2.")

    try:
        response = await llm.ainvoke(langchain_messages)
        clean = extract_text(response.content)
        if clean.startswith("```json"): clean = clean[7:]
        if clean.startswith("```"): clean = clean[3:]
        if clean.endswith("```"): clean = clean[:-3]
        parsed = json.loads(clean.strip())
        
        spoken = parsed.get("ai_response", "Please go ahead and write the code in the editor.")
        advance = parsed.get("advance_to_coding", True)
        
        return {
            "spoken_response": spoken,
            "current_phase": "P2 Coding" if advance else "P2 Approach",
            "editor_unlocked": True
        }
    except Exception:
        return {
            "spoken_response": "That approach makes complete sense. Please go ahead and write the code in the editor.",
            "current_phase": "P2 Coding",
            "editor_unlocked": True
        }

async def p2_coding_and_verify_node(state: InterviewState) -> Dict[str, Any]:
    """Verifies Q2 code submission/test results and asks for Time/Space complexity and a scaling follow-up."""
    llm = get_llm()
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    q2 = state.get("current_problem") or PROBLEMS["merge_intervals"]
    test_results = state.get("test_results") or {}
    editor_code = state.get("editor_code", "")
    language = state.get("language", "python")
    messages = state.get("messages", [])

    all_passed = test_results.get("all_passed", False)
    total_passed = test_results.get("total_passed", 0)
    total_tests = test_results.get("total_tests", 0)
    followup = q2.get("followups", ["How would your approach change if the data stream was infinite?"])[0]

    system_prompt = f"""You are {interviewer_name}, Senior Technical Interviewer.
Candidate: {candidate_name}
Problem: {q2['title']}
Code Language: {language}
Test Cases: {total_passed} out of {total_tests} passed. All passed: {all_passed}.
Follow-up Question: {followup}

Candidate's Code:
```{language}
{editor_code}
```

Instructions:
- If tests passed or code is submitted:
  * Acknowledge the implementation.
  * EXPLICITLY ASK for Time Complexity, Space Complexity, and the follow-up question:
    "Great job on the implementation! What is the time and space complexity of your solution, and {followup}"
  * Set "next_phase": "P2 Followup".
- If tests failed:
  * Give a brief hint about the failing case or bug.
  * Set "next_phase": "P2 Coding".

Output valid JSON only:
{{
    "ai_response": "1-2 sentences spoken response",
    "next_phase": "P2 Followup" | "P2 Coding"
}}
"""
    langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="I have submitted my code for Question 2.")

    try:
        response = await llm.ainvoke(langchain_messages)
        clean = extract_text(response.content)
        if clean.startswith("```json"): clean = clean[7:]
        if clean.startswith("```"): clean = clean[3:]
        if clean.endswith("```"): clean = clean[:-3]
        parsed = json.loads(clean.strip())
        
        spoken = parsed.get("ai_response", f"Great job on the code! What is the time and space complexity, and {followup}")
        next_phase = parsed.get("next_phase", "P2 Followup")
        
        return {
            "spoken_response": spoken,
            "current_phase": next_phase,
            "q2_stats": {"passed": total_passed, "total": total_tests, "attempts": 1},
            "editor_unlocked": True
        }
    except Exception:
        return {
            "spoken_response": f"Great job on the implementation! What is the time and space complexity of your solution, and {followup}",
            "current_phase": "P2 Followup",
            "q2_stats": {"passed": total_passed, "total": total_tests, "attempts": 1},
            "editor_unlocked": True
        }

async def p2_followup_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluates candidate's Big-O complexity analysis and follow-up answer, then concludes the interview."""
    llm = get_llm()
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    q2 = state.get("current_problem") or PROBLEMS["merge_intervals"]
    messages = state.get("messages", [])

    system_prompt = f"""You are {interviewer_name}, Senior Technical Interviewer.
Candidate: {candidate_name}
Problem: {q2['title']}

The candidate just answered the Time & Space Complexity and the scaling follow-up question.

Instructions:
- Acknowledge their complexity analysis and scaling explanation in 1 concise sentence.
- Conclude the interview warmly (e.g. "That wraps up our technical interview today. Thank you for your time, and you can review your complete evaluation report on the dashboard!").

Keep response to 1-2 sentences.
"""
    langchain_messages = build_langchain_messages(system_prompt, messages, default_user_text="Here is my complexity analysis and follow-up answer.")

    try:
        response = await llm.ainvoke(langchain_messages)
        spoken = extract_text(response.content)
    except Exception:
        spoken = f"Spot on with the complexity and scaling analysis! That concludes our technical interview today. Thank you so much, {candidate_name}!"

    return {
        "spoken_response": spoken,
        "current_phase": "Wrap-up",
        "is_concluded": True,
        "editor_unlocked": False
    }

async def wrapup_node(state: InterviewState) -> Dict[str, Any]:
    """Concludes the interview with constructive summary and marks session as concluded."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    spoken = f"Thank you so much, {candidate_name}! That concludes our technical interview today. You demonstrated strong problem-solving and communication skills. I've prepared your full evaluation report on the dashboard."

    return {
        "spoken_response": spoken,
        "current_phase": "Wrap-up",
        "is_concluded": True,
        "editor_unlocked": False
    }
