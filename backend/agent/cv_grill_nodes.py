import os
import json
import time
import random
import logging
from typing import Dict, Any, Optional, List

from google import genai

try:
    from agent.state import InterviewState
except (ImportError, ModuleNotFoundError):
    from .state import InterviewState

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ---------------------------------------------------------------------------
# System prompt — updated to 25-30 min, ~18-20 turns, full CV coverage
# ---------------------------------------------------------------------------
CV_SYSTEM_PROMPT = """You are {interviewer_name}, a friendly, sharp, and highly supportive Senior Software Engineer and Interviewer conducting an Entry-Level (SDE-1 / Junior / New Grad) CV & Project Mock Interview with candidate {candidate_name}.

YOUR GOAL:
Conduct an engaging, realistic, 25-30 minute technical interview based on the candidate's actual CV/Resume. Probe into their hands-on coding, implementation details, project ownership, problem-solving, and fundamentals. Try to touch EVERY project and key skill listed on their CV.

INTERVIEW LEVEL & CALIBRATION:
- Target Level: Entry Level / SDE-1 / Junior Engineer.
- Do NOT ask complex distributed systems questions (avoid Raft consensus, multi-region sharding, 50k RPS partition skew, or advanced infrastructure).
- DO focus on:
  1. Architecture & Request Flow: "Walk me through how your API receives a request, processes the logic, and returns a response."
  2. Database & Data Models: "What tables/collections did you create, and why did you choose this database over alternatives?"
  3. Personal Ownership: "Which parts of this project did you write yourself vs using libraries, packages, or tutorials?"
  4. Real-world Bugs & Debugging: "What was the trickiest bug or error you encountered while building this, and how did you diagnose and fix it?"
  5. Edge Cases & Error Handling: "How do you handle invalid inputs, missing fields, or failed requests in your code?"
  6. Testing & Improvements: "How did you test your project, and what would you improve or refactor if you had more time?"

INTERVIEW PACING & STRUCTURE (Total ~25-30 mins, ~18-20 turns):
- Phase 1 (Turns 1-2, ~2-3 mins): Greet candidate, mention you reviewed their CV, LIST all their projects by name, and ask them to pick their favorite or flagship project. WAIT for their response before diving in.
- Phase 2 (Turns 3-8, ~8-10 mins): Flagship Project Deep-Dive. Probe implementation, API design, database models, real bugs, and technical choices.
- Phase 3 (Turns 9-16, ~12-15 mins): Rotate through their OTHER projects, core skills, and work experience from their CV. Each topic gets 2-4 questions. NEVER repeat a project you already discussed.
- Phase 4 (Turn 17+, ~3-5 mins): Wrap up smoothly ONLY after at least 25 minutes have passed. Compliment strong points, give brief constructive feedback, and invite candidate to ask any final questions.

CONVERSATIONAL RULES:
1. Concise: Keep your spoken responses to 2 to 3 sentences (under 50 words). Never lecture.
2. Socratic & Reactive: Always listen to the candidate's previous response and build your next question directly on what they just said.
3. Encourage & Prompt: If the candidate gives a short or vague answer, gently probe for details ("Could you give me a specific example of how that function or query worked?").
4. Stay in Character: You are {interviewer_name}. Never break character.

CANDIDATE CV / RESUME:
\"\"\"
{cv_context}
\"\"\"
"""


def _call_gemini(contents, temperature: float = 0.5) -> str:
    """Call Gemini with fallback models."""
    global client
    if not client:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Could not init client in cv_grill_nodes: {e}")

    if not client:
        return ""

    models_to_try = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=contents,
                config={"temperature": temperature}
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            logger.warning(f"CV grill node generation error with {m}: {e}")
    return ""


def _get_last_user_msg(messages: list) -> str:
    """Extract the last user message from the history."""
    if not messages:
        return ""
    last = messages[-1]
    return last.content if hasattr(last, "content") else (last.get("content") if isinstance(last, dict) else str(last))


def _build_history_str(messages: list, n: int = 8) -> str:
    """Build a formatted history string from the last N messages."""
    if not messages:
        return ""
    return "\n".join([
        f"{getattr(m, 'type', m.get('role', 'msg') if isinstance(m, dict) else 'msg')}: "
        f"{getattr(m, 'content', m.get('content', str(m)) if isinstance(m, dict) else str(m))}"
        for m in messages[-n:]
    ])


def _get_elapsed_minutes(state: InterviewState) -> float:
    """Get elapsed interview time in minutes."""
    start = state.get("start_time", 0)
    if not start:
        return 0.0
    return (time.time() - start) / 60.0


def _pick_next_cv_topic(parsed_cv: dict, discussed_projects: list, cv_topics_covered: list) -> Optional[Dict[str, Any]]:
    """
    Randomly selects the next un-discussed topic from the CV.
    Priority: remaining projects → skills → experience.
    Returns None if everything has been covered.
    """
    # 1. Try remaining projects
    all_projects = parsed_cv.get("projects", [])
    remaining_projects = [p for p in all_projects if p.get("name", "").strip() not in discussed_projects]
    if remaining_projects:
        chosen = random.choice(remaining_projects)
        return {
            "type": "project",
            "name": chosen.get("name", "Project"),
            "context": chosen
        }

    # 2. Try skills not yet discussed
    all_skills = parsed_cv.get("skills", [])
    remaining_skills = [s for s in all_skills if s not in cv_topics_covered]
    if remaining_skills:
        # Pick 2-3 related skills to discuss together
        batch = random.sample(remaining_skills, min(3, len(remaining_skills)))
        return {
            "type": "skill",
            "name": ", ".join(batch),
            "context": batch
        }

    # 3. Try experience entries
    all_exp = parsed_cv.get("experience", [])
    remaining_exp = [e for e in all_exp if e.get("company", "") not in cv_topics_covered]
    if remaining_exp:
        chosen = random.choice(remaining_exp)
        return {
            "type": "experience",
            "name": chosen.get("company", "your previous role"),
            "context": chosen
        }

    # 4. Everything covered
    return None


# ---------------------------------------------------------------------------
# NODE: cv_intro_node — Lists all projects and asks candidate to pick
# ---------------------------------------------------------------------------
async def cv_intro_node(state: InterviewState) -> Dict[str, Any]:
    """Phase 1: Welcome candidate, list ALL their projects, and ask them to pick their favorite."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    cv_summary = state.get("resume_summary", "Software Engineer")
    parsed_cv = state.get("parsed_cv", {})

    # Build a numbered list of ALL projects from the CV
    projects = parsed_cv.get("projects", []) if parsed_cv else []
    if projects:
        project_names = [p.get("name", f"Project {i+1}") for i, p in enumerate(projects)]
        project_list_str = "\n".join([f"  {i+1}. {name}" for i, name in enumerate(project_names)])
        project_mention = f"Here are the projects I found on your CV:\n{project_list_str}"
    else:
        project_mention = "I see you have some interesting projects on your CV"
        project_names = []

    prompt = f"""You are {interviewer_name} starting an Entry-Level (SDE-1) CV Grilling interview with {candidate_name}.
Candidate CV:
{cv_summary[:4000]}

Their projects are:
{project_mention}

Give a warm, friendly opening (2-3 sentences max). Greet {candidate_name}, mention you reviewed their CV, LIST their projects by name (e.g. "I see you've worked on ProjectA, ProjectB, and ProjectC"), and ask them to pick their favorite or flagship project to start with. Do NOT start asking technical questions yet — just ask them to pick one and give a brief overview."""

    spoken = _call_gemini([
        CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
        prompt
    ], temperature=0.5)

    if not spoken:
        if project_names:
            names_str = ", ".join(project_names[:-1]) + f", and {project_names[-1]}" if len(project_names) > 1 else project_names[0]
            spoken = f"Hi {candidate_name}, welcome! I've reviewed your CV and I can see you've worked on some great projects — {names_str}. Which one is your favorite? Pick one and give me a quick overview of what it does and the tech stack you used."
        else:
            spoken = f"Hi {candidate_name}, welcome! I've gone through your CV and I'm excited to learn about your projects. Could you start by telling me about your favorite project — what it does and what tools you used to build it?"

    return {
        "spoken_response": spoken,
        "current_phase": "CV Awaiting Pick",  # Wait for candidate to pick, don't jump to deep-dive
        "turn_count": state.get("turn_count", 0) + 1,
        "editor_unlocked": True
    }


# ---------------------------------------------------------------------------
# NODE: cv_acknowledge_pick_node — Acknowledges the project pick, asks for walkthrough
# ---------------------------------------------------------------------------
async def cv_acknowledge_pick_node(state: InterviewState) -> Dict[str, Any]:
    """Acknowledges the candidate's project selection and asks for a high-level walkthrough."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    cv_summary = state.get("resume_summary", "")
    messages = state.get("messages", [])
    parsed_cv = state.get("parsed_cv", {})
    turn_count = state.get("turn_count", 0) + 1

    last_user_msg = _get_last_user_msg(messages)

    # Try to identify which project the candidate picked
    projects = parsed_cv.get("projects", []) if parsed_cv else []
    picked_project_name = ""
    for p in projects:
        pname = p.get("name", "")
        if pname and pname.lower() in last_user_msg.lower():
            picked_project_name = pname
            break
    
    # If we couldn't match exactly, use whatever they said
    if not picked_project_name:
        picked_project_name = last_user_msg[:80] if last_user_msg else "your chosen project"

    prompt = f"""Candidate's response (they just picked their favorite project):
\"{last_user_msg}\"

The candidate chose to discuss: {picked_project_name}

Acknowledge their choice warmly in 2-3 sentences. Say something like "Great choice!" or "That sounds like an interesting project!" Then ask them to walk you through the high-level architecture — how the system is structured, what the main components are, and what the request flow looks like end-to-end. Do NOT ask multiple deep technical questions yet — just get the overview first."""

    history_str = _build_history_str(messages)

    spoken = _call_gemini([
        CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
        f"Interview History:\n{history_str}",
        prompt
    ], temperature=0.5)

    if not spoken:
        spoken = f"Great choice! {picked_project_name} sounds like a really interesting project. Could you walk me through the high-level architecture — what are the main components and how does a typical request flow through the system?"

    discussed = list(state.get("discussed_projects", []))
    if picked_project_name and picked_project_name not in discussed:
        discussed.append(picked_project_name)

    return {
        "spoken_response": spoken,
        "current_phase": "CV Project Deep Dive",
        "turn_count": turn_count,
        "discussed_projects": discussed,
        "current_cv_topic": picked_project_name,
        "editor_unlocked": True
    }


# ---------------------------------------------------------------------------
# NODE: cv_project_deepdive_node — Deep-dive into a project (time-based transitions)
# ---------------------------------------------------------------------------
async def cv_project_deepdive_node(state: InterviewState) -> Dict[str, Any]:
    """Phase 2/3: Deep dive into the current project — time-gated transitions."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    cv_summary = state.get("resume_summary", "")
    messages = state.get("messages", [])
    parsed_cv = state.get("parsed_cv", {})
    turn_count = state.get("turn_count", 0) + 1
    current_topic = state.get("current_cv_topic", "their project")
    discussed = list(state.get("discussed_projects", []))
    elapsed_min = _get_elapsed_minutes(state)

    last_user_msg = _get_last_user_msg(messages)

    # Count how many turns we've spent on THIS project specifically
    questions_on_topic = 0
    for m in reversed(messages):
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        role = m.get("role", "") if isinstance(m, dict) else getattr(m, "role", "")
        if role == "model" and ("transition" in content.lower() or "let's move" in content.lower() or "next project" in content.lower()):
            break
        if role == "user":
            questions_on_topic += 1
        if questions_on_topic >= 6:
            break

    # Decide whether to stay on this project or move to the next topic
    should_move_on = (questions_on_topic >= 5) or (elapsed_min >= 12 and questions_on_topic >= 3)

    # Check if candidate wants to conclude or we've reached time limit
    is_user_ending = any(kw in last_user_msg.lower() for kw in [
        "end the interview", "wrap up", "conclude", "evaluate", "no questions", "that's all", "nothing from my side", "ready for evaluation", "no more questions", "i'm done", "i am done"
    ])

    if is_user_ending or elapsed_min >= 25:
        return await cv_wrapup_node(state)
    elif should_move_on:
        next_phase = "CV Next Topic"
    else:
        next_phase = "CV Project Deep Dive"

    # Get project-specific context for better questions
    project_context = ""
    if parsed_cv and current_topic:
        for p in parsed_cv.get("projects", []):
            if p.get("name", "") == current_topic:
                project_context = f"\nProject details: {json.dumps(p, default=str)[:1500]}"
                break

    prompt = f"""Candidate's latest response:
\"{last_user_msg}\"

Currently discussing: {current_topic}
{project_context}

Current Phase: Project Deep Dive (Turn {turn_count}, elapsed {elapsed_min:.0f} min of 30 min interview).
Target Level: Entry-Level (SDE-1).
Ask a specific, practical follow-up question digging into their implementation. Choose ONE of these angles based on what they just said:
- How they structured their API endpoints and request-response cycle.
- How they designed their database schema / models and wrote queries.
- Why they picked a specific library/framework over alternatives.
- The hardest bug or error they ran into while coding this and how they debugged it.
- Which specific parts they wrote vs used existing packages.
- How they handled edge cases, error states, or input validation.
- How they tested their code and what they would improve.

Keep your response friendly, inquisitive, and strictly 2-3 spoken sentences. Build directly on what they just said."""

    history_str = _build_history_str(messages)

    spoken = _call_gemini([
        CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
        f"Interview History:\n{history_str}",
        prompt
    ], temperature=0.5)

    if not spoken:
        spoken = "That's really interesting. Can you tell me more about the specific technical challenge you faced while building that feature, and how you went about debugging it?"

    return {
        "spoken_response": spoken,
        "current_phase": next_phase,
        "turn_count": turn_count,
        "discussed_projects": discussed,
        "current_cv_topic": current_topic,
        "editor_unlocked": True
    }


# ---------------------------------------------------------------------------
# NODE: cv_next_topic_node — Randomly selects the next un-discussed topic
# ---------------------------------------------------------------------------
async def cv_next_topic_node(state: InterviewState) -> Dict[str, Any]:
    """Transition node: picks the next un-discussed project/skill/experience from the CV."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    cv_summary = state.get("resume_summary", "")
    messages = state.get("messages", [])
    parsed_cv = state.get("parsed_cv", {})
    turn_count = state.get("turn_count", 0) + 1
    discussed = list(state.get("discussed_projects", []))
    covered = list(state.get("cv_topics_covered", []))
    elapsed_min = _get_elapsed_minutes(state)

    last_user_msg = _get_last_user_msg(messages)

    # Check if we have hit the minimum 25-minute duration to wrap up
    if elapsed_min >= 25:
        return await cv_wrapup_node(state)

    # Pick the next un-discussed topic
    next_topic = _pick_next_cv_topic(parsed_cv, discussed, covered)

    if next_topic is None:
        # All listed CV projects/skills touched, but under 25 mins:
        # Continue deep grilling on system design, scaling, crisis handling & production practices
        prompt = f"""Candidate's response:
\"{last_user_msg}\"

We have covered the main projects on their CV, but the interview has only run for {elapsed_min:.0f} minutes (must reach minimum 25 minutes).
Conduct an in-depth technical grill on advanced engineering principles related to their stack. Pick ONE deep-dive area:
1. Scaling & High Traffic: How they would scale their architecture to handle 100k requests/sec, caching strategies (Redis), or database read-replicas.
2. System Reliability & Incidents: How they monitor errors, write integration tests, handle service outages, and prevent race conditions.
3. API & Database Optimization: Database query profiling, indexing strategies, connection pooling, or rate limiting.
4. Real-world Debugging: A difficult production bug, memory leak, or latency bottleneck they investigated.

Acknowledge their last response briefly, then present this deep-dive scenario/question. Keep it strictly to 2-3 spoken sentences."""

        history_str = _build_history_str(messages)
        spoken = _call_gemini([
            CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
            f"Interview History:\n{history_str}",
            prompt
        ], temperature=0.6)

        if not spoken:
            spoken = "You've walked through your projects really well. Let's dig into system scaling: if your main service experienced a 100x traffic spike tomorrow, what would be the first component to fail, and how would you redesign it with caching and queues?"

        return {
            "spoken_response": spoken,
            "current_phase": "CV Project Deep Dive",
            "turn_count": turn_count,
            "discussed_projects": discussed,
            "cv_topics_covered": covered,
            "editor_unlocked": True
        }

    # Build the transition prompt based on topic type
    if next_topic["type"] == "project":
        project_info = next_topic["context"]
        project_name = next_topic["name"]
        tech_stack = ", ".join(project_info.get("tech_stack", [])) if project_info.get("tech_stack") else "various technologies"
        summary = project_info.get("summary", "")

        prompt = f"""Candidate's response:
\"{last_user_msg}\"

You've finished discussing the previous project. Now smoothly transition to their next project: "{project_name}" (built with {tech_stack}).
Project summary: {summary}

Acknowledge their previous answer briefly, then transition to {project_name}. Ask them to give you a quick overview of what this project does and their specific contribution. Keep it to 2-3 spoken sentences. Make the transition feel natural, not abrupt."""

        discussed.append(project_name)
        next_phase = "CV Project Deep Dive"

    elif next_topic["type"] == "skill":
        skill_names = next_topic["name"]

        prompt = f"""Candidate's response:
\"{last_user_msg}\"

You've discussed their projects. Now transition to asking about specific skills from their CV: {skill_names}.
Acknowledge their previous answer, then ask about their hands-on experience with {skill_names} — how they've used it in practice, what they find challenging about it, or how they learned it. Keep it to 2-3 spoken sentences."""

        for s in next_topic["context"]:
            if s not in covered:
                covered.append(s)
        next_phase = "CV Project Deep Dive"

    else:  # experience
        exp_info = next_topic["context"]
        company = next_topic["name"]
        role = exp_info.get("role", "your role")

        prompt = f"""Candidate's response:
\"{last_user_msg}\"

Now transition to asking about their work experience at {company} as {role}.
Acknowledge their previous answer, then ask about their key contributions at {company}, what they built or shipped, and what they learned. Keep it to 2-3 spoken sentences."""

        covered.append(company)
        next_phase = "CV Project Deep Dive"

    history_str = _build_history_str(messages)

    spoken = _call_gemini([
        CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
        f"Interview History:\n{history_str}",
        prompt
    ], temperature=0.5)

    if not spoken:
        spoken = f"Great insights! Let's move on — I noticed {next_topic['name']} on your CV. Could you tell me about your hands-on experience with that?"

    return {
        "spoken_response": spoken,
        "current_phase": next_phase,
        "turn_count": turn_count,
        "discussed_projects": discussed,
        "current_cv_topic": next_topic["name"],
        "cv_topics_covered": covered,
        "editor_unlocked": True
    }


# ---------------------------------------------------------------------------
# NODE: cv_wrapup_node — Conclude the interview and transition to evaluation
# ---------------------------------------------------------------------------
async def cv_wrapup_node(state: InterviewState) -> Dict[str, Any]:
    """Phase 4: Conclude interview, share positive feedback, and transition directly to evaluation."""
    candidate_name = state.get("candidate_name", "Candidate")
    interviewer_name = state.get('interviewer_name', 'Sanya')
    cv_summary = state.get("resume_summary", "")
    messages = state.get("messages", [])
    elapsed_min = _get_elapsed_minutes(state)

    prompt = f"""Wrap up this 25-30 minute Entry-Level CV Grilling & Project Deep-Dive interview with {candidate_name}.
The interview has run for {elapsed_min:.0f} minutes and covered their key projects, architecture choices, and scaling scenarios.
Thank them warmly for walking through their implementation details, highlight their technical reasoning, and state that their full evaluation report is now ready. Keep it warm, concise, and professional in 2-3 sentences."""

    history_str = _build_history_str(messages)

    spoken = _call_gemini([
        CV_SYSTEM_PROMPT.format(interviewer_name=interviewer_name, candidate_name=candidate_name, cv_context=cv_summary[:8000]),
        f"Interview History:\n{history_str}",
        prompt
    ], temperature=0.4)

    if not spoken:
        spoken = f"That wraps up our 25-minute project and CV deep-dive today, {candidate_name}! You did a great job explaining your design choices, trade-offs, and debugging approach. I've prepared your comprehensive evaluation report for you on the dashboard."

    return {
        "spoken_response": spoken,
        "current_phase": "Wrap-up",
        "turn_count": state.get("turn_count", 0) + 1,
        "interview_completed": True,
        "is_concluded": True,
        "editor_unlocked": False
    }
