from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class InterviewState(TypedDict, total=False):
    # Candidate & Session Info
    session_id: str
    candidate_name: str
    interviewer_name: str
    track: str
    track_name: str
    resume_summary: str
    parsed_cv: Optional[Dict[str, Any]]
    turn_count: int
    start_time: float
    duration_seconds: int
    
    # CV Grilling Progress Tracking
    discussed_projects: List[str]         # Names of projects already deep-dived
    current_cv_topic: Optional[str]       # Current project/skill under discussion
    cv_topics_covered: List[str]          # Skills & experience items already touched
    
    # Dialogue & Stage
    messages: List[Dict[str, Any]]
    current_phase: str  # "Intro" | "P1 Approach" | "P1 Coding" | "P1 Complexity" | "P2 Adaptive" | "P2 Approach" | "P2 Coding" | "P2 Followup" | "Wrapup"
    spoken_response: str
    
    # Active Problem & Code Editor
    current_problem: Optional[Dict[str, Any]]
    problems_completed: List[Dict[str, Any]]
    active_problem_id: Optional[str]
    problem_html: Optional[str]
    starter_code: Optional[str]
    editor_code: str
    language: str
    editor_unlocked: bool
    
    # Telemetry & Performance Signals
    test_results: Optional[Dict[str, Any]]
    q1_stats: Dict[str, Any]  # {"passed": 0, "total": 0, "attempts": 0}
    q2_stats: Dict[str, Any]  # {"passed": 0, "total": 0, "attempts": 0}
    hints_history: List[Dict[str, Any]]  # [{"problem_id": str, "type": str, "text": str, "level": int}]
    candidate_approach_optimality: str  # "unknown" | "wrong_ds" | "brute_force" | "optimal"
    time_complexity_evaluation: Optional[Dict[str, Any]]
    space_complexity_evaluation: Optional[Dict[str, Any]]
    followup_notes: Optional[str]
    
    # Final Outcome & Report
    is_concluded: bool
    overall_score: float
    recommendation: str
    section_ratings: Dict[str, float]
    detailed_feedback: Dict[str, Any]
    final_report: Optional[Dict[str, Any]]
