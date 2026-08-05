import os
import json
import random
import time
from fastapi import FastAPI, Form, HTTPException, WebSocket, UploadFile, File, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from google import genai
from google.genai import types
from typing import Optional, List, Dict, Any

from sandbox import execute_code_piston, evaluate_test_cases
from sandbox import execute_code_piston, evaluate_test_cases
from problems_db import PROBLEMS, COMPANY_TRACKS, get_track_problems
from live_gateway import handle_live_interview_ws
from auth import hash_password, verify_password, create_jwt_token, decode_jwt_token
from cv_extractor import extract_text_from_file, parse_cv_with_gemini

load_dotenv()

app = FastAPI(title="AI Mock Interview Platform Backend")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        db = mongo_client["ai_interview_db"]
        reports_collection = db["reports"]
        users_collection = db["users"]
        
        # Ensure indexes
        users_collection.create_index([("username", ASCENDING)], unique=True)
        reports_collection.create_index([("session_id", ASCENDING)], unique=True)
        reports_collection.create_index([("username", ASCENDING)])
        print("Connected to MongoDB (users, reports collections ready).")
    except Exception as e:
        print(f"Warning: Failed to connect to MongoDB: {e}")
        reports_collection = None
        users_collection = None
else:
    print("Warning: MONGODB_URI not found. Reports will not be saved.")
    reports_collection = None
    users_collection = None

# Gemini setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found. AI responses will fail.")
    genai_client = None

# In-memory storage for active sessions
sessions = {}

class RegisterRequest(BaseModel):
    username: str
    name: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class InterviewSession:
    def __init__(self, session_id: str, track: str = "medium", candidate_name: str = "Candidate", resume_summary: str = "", username: str = "", parsed_cv: Optional[Dict[str, Any]] = None, interviewer_name: str = "Sanya"):
        self.session_id = session_id
        self.track = track
        self.candidate_name = candidate_name
        self.resume_summary = resume_summary
        self.username = username.strip().lower()
        self.interviewer_name = interviewer_name
        self.current_phase = "CV Intro" if track == "cv_grill" else "Intro"
        self.active_problem_id = None
        self.parsed_cv = parsed_cv or {}
        
        q1, q2, track_cfg = get_track_problems(track)
        self.q1 = q1
        self.q2 = q2
        self.track_name = track_cfg["name"]
        self.duration_seconds = 1800 if track == "cv_grill" else 3600  # 30 min for cv_grill, 1 hour (60 min) for all other tracks
        
        self.history = [] # Stores {"role": "user"|"model", "content": text}
        self.q1_code = ""
        self.q2_code = ""
        self.test_stats = {"q1_passed": 0, "q1_total": 0, "q2_passed": 0, "q2_total": 0}
        self.debug_events = [] # Stores chronological execution/compilation/debugging events
        self.hints_history = []
        self.turn_count = 0
        self.start_time = time.time()
        
        # CV Grilling progress tracking
        self.discussed_projects = []
        self.cv_topics_covered = []
        self.current_cv_topic = None

@app.get("/")
def read_root():
    return {"message": "AI Interview Backend is running", "live_api": True, "sandbox": True}

@app.get("/api/network-ping")
def network_ping(size_kb: int = 16):
    """Provides dynamic payload for frontend real-time network latency and throughput measurements."""
    size = max(1, min(size_kb, 256))
    payload = "X" * (size * 1024)
    return {
        "timestamp": time.time(),
        "status": "ok",
        "bytes": len(payload),
        "data": payload
    }

@app.post("/api/auth/register")
def register_user(req: RegisterRequest):
    """Registers a new user with username, name, and hashed password."""
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    username = req.username.strip().lower()
    name = req.name.strip()
    password = req.password.strip()

    if not username:
        raise HTTPException(status_code=400, detail="Valid username is required")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = users_collection.find_one({"username": username})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this username already exists")

    pwd_hash = hash_password(password)
    user_doc = {
        "username": username,
        "name": name,
        "password_hash": pwd_hash,
        "created_at": time.time()
    }
    users_collection.insert_one(user_doc)

    token = create_jwt_token({"username": username, "name": name})
    return {
        "status": "success",
        "token": token,
        "user": {"username": username, "name": name}
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    """Authenticates a user and returns a JWT session token."""
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    username = req.username.strip().lower()
    password = req.password.strip()

    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(user.get("password_hash", ""), password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token({"username": username, "name": user.get("name", "Candidate")})
    return {
        "status": "success",
        "token": token,
        "user": {"username": username, "name": user.get("name", "Candidate")}
    }

@app.get("/api/auth/me")
def get_current_user_profile(authorization: Optional[str] = Header(None)):
    """Returns the authenticated user profile from the JWT token."""
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split("Bearer ")[1].strip()
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return {
        "status": "success",
        "user": {
            "username": payload.get("username"),
            "name": payload.get("name")
        }
    }

@app.get("/api/user/interviews")
def get_user_interviews(
    username: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Retrieves all past interview reports for the user."""
    username = ""
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        payload = decode_jwt_token(token)
        if payload:
            username = payload.get("username", "")

    if not username and isinstance(username, str):
        username = username.strip().lower()

    if not username:
        raise HTTPException(status_code=401, detail="User authentication required")

    if reports_collection is None:
        return {"interviews": []}

    try:
        cursor = reports_collection.find(
            {"username": username},
            {"_id": 0}
        ).sort("created_at", DESCENDING)
        
        interviews = list(cursor)
        return {"status": "success", "interviews": interviews}
    except Exception as e:
        print(f"Error fetching user interviews: {e}")
        return {"status": "error", "interviews": []}

@app.get("/api/tracks")
def get_tracks():
    """Returns available company interview tracks."""
    return {
        "tracks": [
            {
                "id": k,
                "name": v["name"],
                "description": v["description"]
            }
            for k, v in COMPANY_TRACKS.items()
        ]
    }

@app.get("/api/user/cv")
def get_user_cv(
    username: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Retrieves existing CV metadata and parsed structure for the user."""
    target_username = username
    if not target_username and authorization and authorization.startswith("Bearer "):
        payload = decode_jwt_token(authorization.split(" ")[1])
        if payload:
            target_username = payload.get("username")
            
    if not target_username or users_collection is None:
        return {"has_cv": False}
        
    user_doc = users_collection.find_one({"username": target_username.strip().lower()})
    if user_doc and user_doc.get("cv_text"):
        return {
            "has_cv": True,
            "filename": user_doc.get("cv_filename", "resume.pdf"),
            "uploaded_at": user_doc.get("cv_uploaded_at", time.time()),
            "preview_text": user_doc.get("cv_text", "")[:400],
            "parsed_data": user_doc.get("cv_parsed_data", {}),
            "character_count": len(user_doc.get("cv_text", ""))
        }
    return {"has_cv": False}

@app.post("/api/user/cv/upload")
async def upload_user_cv(
    file: UploadFile = File(...),
    username: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    """Uploads, extracts text, parses with Gemini, and stores CV in MongoDB."""
    target_username = username
    if not target_username and authorization and authorization.startswith("Bearer "):
        payload = decode_jwt_token(authorization.split(" ")[1])
        if payload:
            target_username = payload.get("username")
            
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
    extracted_text = extract_text_from_file(content, file.filename)
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded CV. Please upload a PDF, DOCX, or TXT file.")
        
    parsed_cv = parse_cv_with_gemini(extracted_text, genai_client)
    
    if target_username and users_collection is not None:
        target_username = target_username.strip().lower()
        users_collection.update_one(
            {"username": target_username},
            {"$set": {
                "cv_text": extracted_text,
                "cv_filename": file.filename,
                "cv_uploaded_at": time.time(),
                "cv_parsed_data": parsed_cv
            }},
            upsert=True
        )
        
    return {
        "status": "success",
        "has_cv": True,
        "filename": file.filename,
        "preview_text": extracted_text[:400],
        "parsed_data": parsed_cv,
        "character_count": len(extracted_text)
    }

@app.post("/api/setup-interview")
def setup_interview(
    session_id: str = Form(...),
    track: str = Form("medium"),
    candidate_name: str = Form("Candidate"),
    resume_summary: str = Form(""),
    username: str = Form(""),
    interviewer_name: str = Form("Sanya")
):
    """Initializes or resets a tailored interview session."""
    parsed_cv = None
    cv_text = resume_summary
    
    # Auto-load CV if present in MongoDB
    if username and users_collection is not None:
        user_doc = users_collection.find_one({"username": username.strip().lower()})
        if user_doc and user_doc.get("cv_text"):
            parsed_cv = user_doc.get("cv_parsed_data", {})
            if not cv_text:
                cv_text = user_doc.get("cv_text", "")
                
    session = InterviewSession(
        session_id=session_id,
        track=track,
        candidate_name=candidate_name,
        resume_summary=cv_text,
        username=username,
        interviewer_name=interviewer_name,
        parsed_cv=parsed_cv
    )
    sessions[session_id] = session
    
    return {
        "status": "success",
        "session_id": session_id,
        "track": track,
        "track_name": session.track_name,
        "duration_seconds": session.duration_seconds,
        "parsed_cv": session.parsed_cv,
        "q1_id": session.q1["id"],
        "q1_title": session.q1["title"],
        "q2_id": session.q2["id"],
        "q2_title": session.q2["title"],
        "q1_starter_codes": session.q1.get("starter_code", {}),
        "q2_starter_codes": session.q2.get("starter_code", {})
    }

@app.get("/api/problem/{problem_id}")
def get_problem_details(
    problem_id: str,
    language: str = "python",
    session_id: Optional[str] = None
):
    """Retrieves problem details and starter code for the requested language."""
    session = sessions.get(session_id) if session_id else None
    
    problem = None
    if session:
        if getattr(session, "current_problem", None) and (session.current_problem.get("id") == problem_id or problem_id in ["active", "current"]):
            problem = session.current_problem
        elif session.q1.get("id") == problem_id:
            problem = session.q1
        elif session.q2.get("id") == problem_id:
            problem = session.q2
        elif problem_id in ["active", "current", "q1"]:
            problem = getattr(session, "current_problem", session.q1)
        elif problem_id == "q2":
            problem = session.q2

    if not problem:
        problem = PROBLEMS.get(problem_id)
        
    if not problem and session:
        problem = getattr(session, "current_problem", session.q1)
        
    if not problem:
        raise HTTPException(status_code=404, detail=f"Problem '{problem_id}' not found")
        
    lang_key = language.lower().strip()
    starter_dict = problem.get("starter_code", {})
    
    if isinstance(starter_dict, dict):
        starter = starter_dict.get(lang_key)
        if not starter:
            if lang_key in ["python", "py", "python3"]:
                starter = starter_dict.get("python") or starter_dict.get("python3")
            elif lang_key in ["cpp", "c++", "c"]:
                starter = starter_dict.get("cpp")
            elif lang_key in ["javascript", "js", "node"]:
                starter = starter_dict.get("javascript")
            elif lang_key in ["java"]:
                starter = starter_dict.get("java")
        if not starter:
            starter = starter_dict.get("python") or (list(starter_dict.values())[0] if starter_dict else "")
    elif isinstance(starter_dict, str):
        starter = starter_dict
    else:
        starter = ""
        
    return {
        "id": problem["id"],
        "title": problem["title"],
        "difficulty": problem.get("difficulty", "Medium"),
        "category": problem.get("category", ["DSA"]),
        "html": problem["html"],
        "starter_code": starter,
        "all_starter_codes": starter_dict if isinstance(starter_dict, dict) else {"python": starter_dict},
        "sample_test_cases": problem.get("sample_test_cases", [])
    }

@app.post("/api/run-code")
async def run_code(request: Request):
    """Runs candidate code against visible sample test cases (accepts JSON and Form)."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        session_id = body.get("session_id", "")
        problem_id = body.get("problem_id", "")
        code = body.get("code", "")
        language = body.get("language", "python")
    else:
        form = await request.form()
        session_id = form.get("session_id", "")
        problem_id = form.get("problem_id", "")
        code = form.get("code", "")
        language = form.get("language", "python")

    session = sessions.get(session_id)
    problem = None
    if session:
        if getattr(session, "current_problem", None) and session.current_problem.get("id") == problem_id:
            problem = session.current_problem
        elif session.q1.get("id") == problem_id:
            problem = session.q1
        elif session.q2.get("id") == problem_id:
            problem = session.q2
    if not problem:
        problem = PROBLEMS.get(problem_id)
    if not problem and session:
        problem = getattr(session, "current_problem", session.q1)

    if not problem:
        return execute_code_piston(language, code)
        
    test_cases = problem.get("sample_test_cases", [])
    results = evaluate_test_cases(language, code, test_cases, problem_id)
    
    if session:
        errors = [r["error"] for r in results.get("results", []) if r.get("error")]
        if errors:
            first_err = errors[0].strip().splitlines()[-1] if errors[0] else "Runtime Error"
            session.debug_events.append(f"Ran code on {problem['title']}: Encountered error ({first_err[:70]}).")
        elif results.get("all_passed"):
            session.debug_events.append(f"Ran code on {problem['title']}: Successfully passed all {results['total_passed']}/{results['total_tests']} sample tests.")
        else:
            session.debug_events.append(f"Ran code on {problem['title']}: Passed {results['total_passed']}/{results['total_tests']} sample tests.")

    return results

@app.post("/api/submit-solution")
async def submit_solution(request: Request):
    """Runs candidate code against hidden test cases for evaluation (accepts JSON and Form)."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        session_id = body.get("session_id", "")
        problem_id = body.get("problem_id", "")
        code = body.get("code", "")
        language = body.get("language", "python")
    else:
        form = await request.form()
        session_id = form.get("session_id", "")
        problem_id = form.get("problem_id", "")
        code = form.get("code", "")
        language = form.get("language", "python")

    session = sessions.get(session_id)
    problem = None
    if session:
        if getattr(session, "current_problem", None) and session.current_problem.get("id") == problem_id:
            problem = session.current_problem
        elif session.q1.get("id") == problem_id:
            problem = session.q1
        elif session.q2.get("id") == problem_id:
            problem = session.q2
    if not problem:
        problem = PROBLEMS.get(problem_id)
    if not problem and session:
        problem = getattr(session, "current_problem", session.q1)

    if not problem:
        return {"error": "Problem not found"}
        
    all_tests = problem.get("sample_test_cases", []) + problem.get("hidden_test_cases", [])
    results = evaluate_test_cases(language, code, all_tests, problem_id)
    
    if session:
        if problem_id == session.q1["id"]:
            session.q1_code = code
            session.test_stats["q1_passed"] = results["total_passed"]
            session.test_stats["q1_total"] = results["total_tests"]
        elif problem_id == session.q2["id"]:
            session.q2_code = code
            session.test_stats["q2_passed"] = results["total_passed"]
            session.test_stats["q2_total"] = results["total_tests"]
            
        errors = [r["error"] for r in results.get("results", []) if r.get("error")]
        if errors:
            first_err = errors[0].strip().splitlines()[-1] if errors[0] else "Runtime Error"
            session.debug_events.append(f"Submitted code for {problem['title']}: Encountered error ({first_err[:70]}).")
        elif results.get("all_passed"):
            session.debug_events.append(f"Submitted code for {problem['title']}: Passed all {results['total_passed']}/{results['total_tests']} test cases.")
        else:
            session.debug_events.append(f"Submitted code for {problem['title']}: Passed {results['total_passed']}/{results['total_tests']} test cases.")

    return results

def construct_system_prompt(session: InterviewSession, code: str, language: str, is_final: bool) -> str:
    """Builds the comprehensive system prompt for interview evaluation."""
    if is_final:
        duration_sec = int(time.time() - session.start_time)
        duration_str = f"{max(1, round(duration_sec / 60))} minute(s)" if duration_sec >= 60 else f"{duration_sec} seconds"
        history_summary = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in session.history]) if session.history else "(No conversation recorded)"

        # Specialized CV Grilling Evaluation Prompt
        if session.track == "cv_grill":
            parsed_projects = session.parsed_cv.get("projects", []) if session.parsed_cv else []
            projects_str = ", ".join([p.get("name", "Project") for p in parsed_projects]) or "Candidate Projects"
            return f"""You are {session.interviewer_name}, Senior Staff Engineer and Technical Interviewer concluding a 25-30 minute CV / Resume Grilling & Project Deep-Dive interview.
Candidate: {session.candidate_name}
Target Track: CV & Project Architecture Deep-Dive
Total Duration: {duration_str}
Projects on CV: {projects_str}
Candidate CV Summary: {session.resume_summary[:1000]}

Transcript:
{history_summary}

EVALUATION GOAL:
Provide a rigorous, evidence-grounded assessment of the candidate's actual engineering depth, architectural reasoning, trade-off justifications, scaling foresight, and hands-on ownership of their projects.

Output ONLY valid JSON matching this schema:
{{
    "ai_response": "<Spoken concluding remarks from {session.interviewer_name} summarizing performance in 2-3 sentences>",
    "overall_score": <float between 0.0 and 10.0>,
    "recommendation": "<'Strong Hire' | 'Hire' | 'Lean Hire' | 'Needs Improvement' | 'No Hire'>",
    "total_questions_attempted": "{len(parsed_projects)} Projects Discussed",
    "section_ratings": {{
        "system_architecture": <float 0.0-10.0>,
        "technical_tradeoffs": <float 0.0-10.0>,
        "project_authenticity": <float 0.0-10.0>,
        "crisis_handling": <float 0.0-10.0>
    }},
    "detailed_feedback": {{
        "system_architecture": {{
            "score": <float>,
            "good_parts": ["<Observation on data flow, component design, schema, and API structure>"],
            "bad_parts": ["<Gaps or unaddressed bottlenecks>"]
        }},
        "technical_tradeoffs": {{
            "score": <float>,
            "good_parts": ["<Observation on justification of tech stack and database/queue choices>"],
            "bad_parts": ["<Superficial justifications or missing alternatives>"]
        }},
        "project_authenticity": {{
            "score": <float>,
            "good_parts": ["<Evidence of hands-on contribution and low-level debugging knowledge>"],
            "bad_parts": ["<Vague answers or buzzword reliance>"]
        }},
        "crisis_handling": {{
            "score": <float>,
            "good_parts": ["<How candidate handled 50x traffic spikes, cache breakdowns, and concurrency>"],
            "bad_parts": ["<Failure to identify single points of failure>"]
        }}
    }}
}}
"""
        
        # Determine actual questions attempted
        questions_attempted = 0
        if session.current_phase in ["Question 1", "Question 1 Follow-up"]:
            questions_attempted = 1
        elif session.current_phase in ["Question 2", "Question 2 Follow-up", "Wrap-up"]:
            questions_attempted = 2
        elif session.test_stats["q2_total"] > 0:
            questions_attempted = 2
        elif session.test_stats["q1_total"] > 0:
            questions_attempted = 1

        debug_timeline = "\n".join([f"- {event}" for event in getattr(session, "debug_events", [])]) if getattr(session, "debug_events", None) else "- No code execution errors logged."

        q2_obj = getattr(session, "q2", PROBLEMS.get("merge-intervals", {}))
        q1_code_str = session.q1_code or "(No code submitted for Q1)"
        q2_code_str = session.q2_code or (code if session.current_phase in ["P2 Coding", "P2 Followup", "Wrap-up"] else "(No code submitted for Q2)")

        return f"""You are {session.interviewer_name}, a Senior Technical Interviewer at a top tech company concluding the interview.
You must perform an ACCURATE, NATURAL, and EVIDENCE-BASED evaluation of the candidate's ACTUAL performance in this interview session.

=== SESSION FACTS ===
- Candidate Name: {session.candidate_name}
- Target Track: {session.track_name}
- Total Duration: {duration_str}
- Final Phase Reached: {session.current_phase}
- DSA Questions Attempted: {questions_attempted} of 2
- Test Cases Passed:
  * Question 1: {session.q1['title']} ({session.q1.get('difficulty', 'Medium')}) -> {session.test_stats['q1_passed']}/{session.test_stats['q1_total']} passed
  * Question 2: {q2_obj.get('title', 'Question 2')} ({q2_obj.get('difficulty', 'Hard')}) -> {session.test_stats['q2_passed']}/{session.test_stats['q2_total']} passed

=== CANDIDATE SUBMITTED CODES ===
- Question 1 Code ({session.q1['title']}):
```{language}
{q1_code_str}
```

- Question 2 Code ({q2_obj.get('title', 'Question 2')}):
```{language}
{q2_code_str}
```

=== REAL CODE EXECUTION & DEBUGGING TIMELINE ===
{debug_timeline}

- Complete Conversation Transcript:
{history_summary}

=== EVALUATION & SCORING RULES ===
1. BE ACCURATE AND GROUNDED IN REAL EVENTS:
   - In "Coding Skills" and "Debugging & Iteration", explicitly mention what actually happened during code execution:
     * If they ran into a compilation error or syntax error and fixed it, mention: "Encountered a syntax/compilation error initially, then debugged and resolved it."
     * If all tests passed on the first run, mention: "Clean code implementation with zero compilation errors."
     * If they needed hints or adjusted their approach (e.g. from brute force to optimal), reflect that accurately.
     * If they accurately explained Big-O complexity, acknowledge their time and space complexity analysis.
   - Keep bullet points concise, human, and authentic (1 short sentence per bullet). Avoid generic filler.

Output ONLY valid JSON matching this schema:
{{
    "ai_response": "<Concise spoken concluding remarks from {session.interviewer_name} directly addressing the candidate>",
    "overall_score": <float between 0.0 and 10.0 representing true performance>,
    "recommendation": "<'Strong Hire' | 'Hire' | 'Lean Hire' | 'Needs Improvement' | 'No Hire (Incomplete)'>",
    "total_questions_attempted": "<'0 / 2' | '1 / 2' | '2 / 2'>",
    "section_ratings": {{
        "self_introduction": <float between 0.0 and 10.0>,
        "dsa": <float between 0.0 and 10.0>
    }},
    "detailed_feedback": {{
        "self_introduction": {{
            "score": <float>,
            "good_parts": ["<bullet 1 based on actual intro>", "<bullet 2>"],
            "bad_parts": ["<bullet 1>", "<bullet 2>"]
        }},
        "dsa": {{
            "score": <float>,
            "subsections": [
                {{
                    "title": "Problem Solving Ability",
                    "score": <float>,
                    "good_parts": ["<specific observation on algorithm/data structure choice>"],
                    "bad_parts": ["<specific observation>"]
                }},
                {{
                    "title": "Coding Skills",
                    "score": <float>,
                    "good_parts": ["<specific observation on code structure or syntax>"],
                    "bad_parts": ["<specific observation>"]
                }},
                {{
                    "title": "Communication & Collaboration",
                    "score": <float>,
                    "good_parts": ["<specific observation on explanation & responsiveness to hints>"],
                    "bad_parts": ["<specific observation>"]
                }},
                {{
                    "title": "Debugging & Iteration",
                    "score": <float>,
                    "good_parts": ["<specific observation on test runs, error resolution, dry runs>"],
                    "bad_parts": ["<specific observation>"]
                }}
            ]
        }}
    }}
}}
"""

def generate_final_report(session: InterviewSession, code: str, language: str, fallback_spoken: str = "") -> dict:
    """Synthesizes an evidence-grounded final evaluation report using Gemini and actual session telemetry."""
    duration_sec = int(time.time() - session.start_time)
    q2_obj = getattr(session, "q2", PROBLEMS.get("merge_intervals", {}))
    
    system_prompt = construct_system_prompt(session, code, language, is_final=True)
    
    parsed = None
    if genai_client:
        models_to_try = ['gemini-3.1-flash-lite', 'gemini-3.5-flash', 'gemini-2.5-flash']
        contents = [
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])]
            )
            for msg in session.history[-20:]
        ] if session.history else [types.Content(role="user", parts=[types.Part.from_text(text="Generate evaluation report.")])]

        for model_name in models_to_try:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    temperature=0.4,
                    response_mime_type="application/json"
                )
                response = genai_client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                clean_text = response.text.strip()
                if clean_text.startswith("```json"): clean_text = clean_text[7:]
                if clean_text.startswith("```"): clean_text = clean_text[3:]
                if clean_text.endswith("```"): clean_text = clean_text[:-3]
                parsed = json.loads(clean_text.strip())
                break
            except Exception as e:
                print(f"Error generating AI evaluation report with {model_name}: {e}")
                continue

    is_cv_track = session.track == "cv_grill"

    # Fallback if AI call fails
    if not parsed:
        if is_cv_track:
            parsed = {
                "ai_response": fallback_spoken or "Thank you for completing the CV and project architecture deep-dive! You can review your full evaluation report on the dashboard.",
                "overall_score": 8.0,
                "recommendation": "Hire",
                "total_questions_attempted": "4 / 4 Probing Areas",
                "section_ratings": {
                    "system_architecture": 8.0,
                    "technical_tradeoffs": 7.5,
                    "project_authenticity": 8.5,
                    "crisis_handling": 7.5
                },
                "detailed_feedback": {
                    "system_architecture": {
                        "score": 8.0,
                        "good_parts": ["Clearly articulated backend system architecture, API boundaries, and database models."],
                        "bad_parts": []
                    },
                    "technical_tradeoffs": {
                        "score": 7.5,
                        "good_parts": ["Justified technology choices and library selections rationally."],
                        "bad_parts": []
                    },
                    "project_authenticity": {
                        "score": 8.5,
                        "good_parts": ["Demonstrated deep first-hand knowledge of code structure and debugging experiences."],
                        "bad_parts": []
                    },
                    "crisis_handling": {
                        "score": 7.5,
                        "good_parts": ["Reasoned through failure modes, edge cases, and high-traffic scenarios."],
                        "bad_parts": []
                    }
                }
            }
        else:
            had_errors = any("error" in e.lower() for e in getattr(session, "debug_events", []))
            debugging_good = ["Encountered syntax/compilation error initially, then debugged and resolved it."] if had_errors else ["Clean code implementation with zero compilation errors."]
            
            parsed = {
                "ai_response": fallback_spoken or "Thank you for completing the interview! You can review your full evaluation report on the dashboard.",
                "overall_score": 8.5 if session.test_stats["q2_passed"] > 0 else (6.0 if session.test_stats["q1_passed"] > 0 else 3.0),
                "recommendation": "Strong Hire" if session.test_stats["q2_passed"] > 0 else "Hire",
                "total_questions_attempted": "2 / 2" if session.test_stats["q2_passed"] > 0 else "1 / 2",
                "section_ratings": {
                    "self_introduction": 8.0,
                    "dsa": 8.5 if session.test_stats["q2_passed"] > 0 else 6.0
                },
                "detailed_feedback": {
                    "self_introduction": {
                        "score": 8.0,
                        "good_parts": ["Clearly communicated technical background and experience."],
                        "bad_parts": []
                    },
                    "dsa": {
                        "score": 8.5 if session.test_stats["q2_passed"] > 0 else 6.0,
                        "subsections": [
                            {
                                "title": "Problem Solving Ability",
                                "score": 8.5,
                                "good_parts": ["Arrived at optimal algorithmic approaches."],
                                "bad_parts": []
                            },
                            {
                                "title": "Coding Skills",
                                "score": 8.0,
                                "good_parts": ["Structured code cleanly with appropriate variable names."],
                                "bad_parts": []
                            },
                            {
                                "title": "Communication & Collaboration",
                                "score": 8.5,
                                "good_parts": ["Articulated reasoning clearly and explained Big-O complexity accurately."],
                                "bad_parts": []
                            },
                            {
                                "title": "Debugging & Iteration",
                                "score": 8.5,
                                "good_parts": debugging_good,
                                "bad_parts": []
                            }
                        ]
                    }
                }
            }

    report_doc = {
        "session_id": session.session_id,
        "username": getattr(session, "username", ""),
        "candidate_name": session.candidate_name,
        "track": session.track,
        "track_name": session.track_name,
        "skills_assessed": "CV & System Architecture Deep-Dive" if is_cv_track else "Technical Interview (DSA & Problem Solving)",
        "overall_score": parsed.get("overall_score", 8.0),
        "recommendation": parsed.get("recommendation", "Hire"),
        "duration_seconds": duration_sec,
        "total_time_minutes": max(1, round(duration_sec / 60)) if duration_sec >= 60 else f"{duration_sec}s",
        "total_questions": parsed.get("total_questions_attempted", "4 / 4 Probing Areas") if is_cv_track else "2 / 2",
        "total_questions_attempted": parsed.get("total_questions_attempted", "4 / 4 Probing Areas" if is_cv_track else "2 / 2"),
        "q1_title": "Project Architecture & CV Deep-Dive" if is_cv_track else session.q1["title"],
        "q2_title": "Follow-up Tradeoffs & Scaling" if is_cv_track else q2_obj.get("title", "Question 2"),
        "q1_code": session.q1_code or code,
        "q2_code": session.q2_code or code,
        "test_stats": session.test_stats,
        "debug_events": getattr(session, "debug_events", []),
        "section_ratings": parsed.get("section_ratings", {"system_architecture": 8.0, "technical_tradeoffs": 7.5, "project_authenticity": 8.0, "crisis_handling": 7.5} if is_cv_track else {"self_introduction": 8.0, "dsa": 8.0}),
        "detailed_feedback": parsed.get("detailed_feedback", {}),
        "evaluation_report": parsed.get("ai_response", fallback_spoken),
        "created_at": time.time()
    }

    if reports_collection is not None:
        try:
            reports_collection.update_one(
                {"session_id": session.session_id},
                {"$set": report_doc},
                upsert=True
            )
        except Exception as e:
            print(f"Failed to save MongoDB report: {e}")

    return report_doc

    active_problem = session.q2 if session.current_phase in ["Question 2", "Question 2 Follow-up"] else session.q1
    session.active_problem_id = active_problem["id"]

    return f"""You are {session.interviewer_name}, an expert Senior Technical Interviewer conducting a realistic live DSA interview on the {session.track_name} track.
Candidate Name: {session.candidate_name}
Candidate Background / Resume: {session.resume_summary or 'Computer Science / Software Engineering'}

STRICT INTERVIEW DIALOGUE & PHASE RULES:

1. "Intro" Phase:
   - Turn 1: Greet candidate warmly by name, ask 1 brief background or tech stack question.
   - Turn 2: As soon as the candidate answers or introduces themselves, acknowledge in 1 sentence and IMMEDIATELY transition to "Question 1" ({session.q1['title']}).
     * Set "current_phase": "Question 1", "editor_unlocked": true, "problem_id": "{session.q1['id']}".
     * Present the problem clearly and ask: "Could you share your initial thoughts and approach for solving this?"

2. "Question 1" ({session.q1['title']}):
   - Step A (Approach Discussion):
     * If the candidate suggests a brute-force approach (e.g. O(N^2)), acknowledge it and ask: "That works, but can we optimize the time complexity?"
     * If the candidate suggests an optimal or solid approach (e.g. hash map / two pointers / sorting), acknowledge enthusiastically and EXPLICITLY TELL THEM TO WRITE CODE:
       "That sounds like a great approach! Please go ahead and write the code in the editor."
       (Keep "current_phase": "Question 1", "editor_unlocked": true).
   - Step B (Coding & Execution):
     * The candidate writes and tests code in the sandbox.
     * If they ask for hints, provide subtle Socratic guidance without giving the full solution.
     * When their test cases pass or they submit their code, acknowledge: "Excellent job passing the tests! Let's discuss the time and space complexity."
       (Transition "current_phase": "Question 1 Follow-up").
   - Step C (Complexity & Follow-up):
     * Ask: "What is the time complexity and space complexity of your solution?"
     * When answered correctly, transition to "Question 2" ({session.q2['title']}).
     * Set "current_phase": "Question 2", "editor_unlocked": true, "problem_id": "{session.q2['id']}".

3. "Question 2" ({session.q2['title']}):
   - Step A (Approach Discussion):
     * Ask for their approach to Question 2.
     * When they provide an approach, approve it and tell them to code.
   - Step B (Coding & Execution):
     * Candidate codes and tests Question 2.
   - Step C (Complexity & Follow-up):
     * Ask for Big-O analysis and 1 scale/constraint follow-up.
     * When finished, transition to "Wrap-up".

4. "Wrap-up" Phase:
   - Provide warm concluding remarks and praise their problem-solving.

Output ONLY valid JSON matching this schema:
{{
    "ai_response": "<Spoken reply from {session.interviewer_name} to candidate (1-3 conversational sentences)>",
    "current_phase": "<'Intro' | 'Question 1' | 'Question 1 Follow-up' | 'Question 2' | 'Question 2 Follow-up' | 'Wrap-up'>",
    "editor_unlocked": <true | false>,
    "problem_id": "<'{session.q1['id']}' | '{session.q2['id']}' | null>",
    "problem_html": "<HTML description if presenting problem, otherwise null>",
    "starter_code": "<starter code if presenting problem, otherwise null>"
}}
"""

from agent.graph import execute_agent_turn
from agent.state import InterviewState

@app.post("/api/interview-stream")
@app.post("/api/submit")
async def submit_text(
    session_id: str = Form(...),
    language: str = Form("python"),
    code: Optional[str] = Form(""),
    current_code: Optional[str] = Form(""),
    transcription: Optional[str] = Form(""),
    text_input: Optional[str] = Form(""),
    is_final: Optional[bool] = Form(False),
    is_final_submission: Optional[bool] = Form(False),
    is_opening_greeting: Optional[bool] = Form(False),
    is_quick_advance: Optional[bool] = Form(False)
):
    if session_id not in sessions:
        sessions[session_id] = InterviewSession(session_id)
        
    session = sessions[session_id]
    
    # Unify input flags and text
    active_code = current_code if current_code else (code or "")
    is_final_flag = (is_final is True or str(is_final).lower() in ["true", "1"]) or \
                    (is_final_submission is True or str(is_final_submission).lower() in ["true", "1"])
    is_opening = is_opening_greeting is True or str(is_opening_greeting).lower() in ["true", "1"]
    is_advance = is_quick_advance is True or str(is_quick_advance).lower() in ["true", "1"]

    raw_user_msg = (text_input or transcription or "").strip()
    
    # Handle initial vs ongoing user message
    if is_opening or (not session.history and not raw_user_msg):
        user_message = f"Hi {session.interviewer_name}, I am {session.candidate_name} and I am ready to start the interview."
    elif is_advance:
        user_message = "I have given my introduction and I am ready to begin Question 1. Please give me the first coding problem."
        session.current_phase = "P1 Approach"
    elif not raw_user_msg and session.current_phase == "Intro" and len(session.history) >= 2:
        user_message = "I have given my introduction and I am ready to begin the first coding question."
    elif not raw_user_msg and session.current_phase not in ["Intro", "Wrap-up"]:
        user_message = "Here is my current code implementation. Could you review it?"
    else:
        user_message = raw_user_msg
        
    if user_message:
        session.history.append({"role": "user", "content": user_message})

    # If this is the final report evaluation request, call the evaluation model
    is_concluded_phase = session.current_phase in ["Wrap-up", "CV Wrap-up", "Completed"]
    if is_final_flag or is_concluded_phase:
        system_prompt = construct_system_prompt(session, active_code, language, is_final=True)
        contents = [
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])]
            )
            for msg in session.history[-15:]
        ]
        models_to_try = ['gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-3.5-flash']
        parsed_response = None
        for model_name in models_to_try:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    temperature=0.7,
                    response_mime_type="application/json"
                )
                response = genai_client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                parsed_response = json.loads(response.text)
                break
            except Exception as e:
                print(f"Evaluation model {model_name} error: {e}")
                continue

        if not parsed_response:
            parsed_response = {
                "ai_response": "Thank you for completing the technical interview today.",
                "current_phase": "Wrap-up",
                "editor_unlocked": False
            }
        
        spoken_response = parsed_response.get("ai_response", "Thank you for completing the interview.")
        session.history.append({"role": "model", "content": spoken_response})

        duration_sec = int(time.time() - session.start_time)
        q_attempted = 0
        if session.current_phase in ["P1 Approach", "P1 Coding", "P1 Complexity", "Question 1", "Question 1 Follow-up"]:
            q_attempted = 1
        elif session.current_phase in ["P2 Approach", "P2 Coding", "P2 Followup", "Question 2", "Question 2 Follow-up", "Wrap-up"]:
            q_attempted = 2
        elif session.test_stats["q2_total"] > 0:
            q_attempted = 2
        elif session.test_stats["q1_total"] > 0:
            q_attempted = 1

        default_overall = 2.0 if q_attempted == 0 else (4.5 if q_attempted == 1 else 7.0)
        default_dsa = 0.0 if q_attempted == 0 else (4.0 if q_attempted == 1 else 7.0)

        report_doc = {
            "session_id": session_id,
            "username": getattr(session, "username", ""),
            "candidate_name": session.candidate_name,
            "track": session.track,
            "track_name": session.track_name,
            "skills_assessed": "Technical Interview (DSA & Problem Solving)",
            "overall_score": parsed_response.get("overall_score", default_overall),
            "recommendation": parsed_response.get("recommendation", "Incomplete" if q_attempted == 0 else "Needs Improvement"),
            "duration_seconds": duration_sec,
            "total_time_minutes": max(1, round(duration_sec / 60)) if duration_sec >= 60 else f"{duration_sec}s",
            "total_questions": parsed_response.get("total_questions_attempted", f"{q_attempted} / 2"),
            "total_questions_attempted": parsed_response.get("total_questions_attempted", f"{q_attempted} / 2"),
            "q1_title": session.q1["title"],
            "q2_title": session.q2["title"],
            "q1_code": session.q1_code or active_code,
            "q2_code": session.q2_code,
            "test_stats": session.test_stats,
            "section_ratings": parsed_response.get("section_ratings", {
                "self_introduction": 5.0,
                "dsa": default_dsa
            }),
            "detailed_feedback": parsed_response.get("detailed_feedback", {}),
            "evaluation_report": spoken_response,
            "created_at": time.time()
        }
        parsed_response["report_data"] = report_doc
        parsed_response["interviewer_response"] = spoken_response
        parsed_response["interview_ended"] = True
        
        if reports_collection is not None:
            try:
                reports_collection.update_one(
                    {"session_id": session_id},
                    {"$set": report_doc},
                    upsert=True
                )
            except Exception as e:
                print(f"Failed to save MongoDB report: {e}")

        return parsed_response

    # Normal interview turn: Execute via LangGraph Agent
    session.turn_count = getattr(session, "turn_count", 0) + 1
    current_problem = getattr(session, "current_problem", session.q1)
    agent_state: InterviewState = {
        "session_id": session_id,
        "candidate_name": session.candidate_name,
        "track": session.track,
        "track_name": session.track_name,
        "resume_summary": session.resume_summary,
        "parsed_cv": getattr(session, "parsed_cv", {}),
        "turn_count": session.turn_count,
        "start_time": session.start_time,
        "messages": session.history,
        "current_phase": session.current_phase,
        "current_problem": current_problem,
        "active_problem_id": session.active_problem_id or current_problem["id"],
        "editor_code": active_code,
        "language": language,
        "q1_stats": {"passed": session.test_stats["q1_passed"], "total": session.test_stats["q1_total"]},
        "q2_stats": {"passed": session.test_stats["q2_passed"], "total": session.test_stats["q2_total"]},
        "hints_history": getattr(session, "hints_history", []),
        "discussed_projects": getattr(session, "discussed_projects", []),
        "current_cv_topic": getattr(session, "current_cv_topic", None),
        "cv_topics_covered": getattr(session, "cv_topics_covered", []),
    }

    agent_result = await execute_agent_turn(agent_state)

    spoken_response = agent_result.get("spoken_response", "Let's continue.")
    new_phase = agent_result.get("current_phase", session.current_phase)
    session.current_phase = new_phase
    
    if agent_result.get("current_problem"):
        session.current_problem = agent_result["current_problem"]
        if new_phase in ["P2 Approach", "P2 Coding", "P2 Followup"]:
            session.q2 = agent_result["current_problem"]
            
    if agent_result.get("active_problem_id"):
        session.active_problem_id = agent_result["active_problem_id"]

    if agent_result.get("hints_history"):
        session.hints_history = agent_result["hints_history"]

    # Persist CV grilling tracking state
    if agent_result.get("discussed_projects") is not None:
        session.discussed_projects = agent_result["discussed_projects"]
    if agent_result.get("cv_topics_covered") is not None:
        session.cv_topics_covered = agent_result["cv_topics_covered"]
    if agent_result.get("current_cv_topic") is not None:
        session.current_cv_topic = agent_result["current_cv_topic"]

    session.history.append({"role": "model", "content": spoken_response})

    # Prepare response payload
    curr_prob = getattr(session, "current_problem", session.q1)
    is_intro = new_phase == "Intro"
    sample_tests = [] if is_intro else curr_prob.get("sample_test_cases", [])
    editor_unlocked = agent_result.get("editor_unlocked", False if is_intro else True)
    active_prob_id = agent_result.get("active_problem_id") if not is_intro else None

    is_ended = (
        new_phase in ["Wrap-up", "CV Wrap-up", "Completed"]
        or agent_result.get("is_concluded", False)
        or agent_result.get("interview_completed", False)
    )

    response_payload = {
        "ai_response": spoken_response,
        "interviewer_response": spoken_response,
        "current_phase": new_phase,
        "editor_unlocked": editor_unlocked,
        "enable_editor": editor_unlocked,
        "problem_id": active_prob_id,
        "active_problem_id": active_prob_id,
        "problem_html": agent_result.get("problem_html") if not is_intro else None,
        "starter_code": agent_result.get("starter_code") if not is_intro else None,
        "all_starter_codes": curr_prob.get("starter_code", {}) if not is_intro else {},
        "sample_test_cases": sample_tests,
        "interview_ended": is_ended
    }

    if is_ended:
        report_doc = generate_final_report(session, active_code, language, spoken_response)
        response_payload["report_data"] = report_doc
        response_payload["evaluation_report"] = report_doc.get("evaluation_report", spoken_response)

    return response_payload

@app.get("/api/reports/{session_id}")
def get_report(session_id: str):
    """Retrieves saved evaluation report from MongoDB."""
    if reports_collection is None:
        raise HTTPException(status_code=404, detail="Database not configured")
        
    doc = reports_collection.find_one({"session_id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    return doc

@app.websocket("/ws/live-interview")
async def live_interview_ws(websocket: WebSocket, session_id: str = "default"):
    """WebSocket endpoint for live bidirectional voice interaction."""
    if not genai_client:
        await websocket.close(code=1008)
        return
    await handle_live_interview_ws(websocket, session_id, genai_client, sessions)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
