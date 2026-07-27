import os
import json
import random
from typing import Dict, Any, List, Optional
try:
    from problems_db import PROBLEMS, INTERVIEW_TIERS, get_adaptive_q2, PROBLEMS_BY_DIFFICULTY
except (ImportError, ModuleNotFoundError):
    from ..problems_db import PROBLEMS, INTERVIEW_TIERS, get_adaptive_q2, PROBLEMS_BY_DIFFICULTY
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

def get_llm(model: str = "gemini-3.1-flash-lite", temperature: float = 0.7):
    api_key = os.getenv("GEMINI_API_KEY")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature
    )

def select_adaptive_problem(
    track: str,
    q1_stats: Dict[str, Any],
    hints_used: int,
    exclude_ids: List[str]
) -> Dict[str, Any]:
    """
    Dynamically select Question 2 based on chosen Tier and Question 1 performance telemetry.
    """
    total_tests = q1_stats.get("total", 0)
    passed_tests = q1_stats.get("passed", 0)
    pass_rate = (passed_tests / total_tests) if total_tests > 0 else 0.0

    struggled = (pass_rate < 1.0) or (hints_used >= 2)
    q1_slug = exclude_ids[0] if exclude_ids else "two-sum"
    
    return get_adaptive_q2(tier_id=track, q1_slug=q1_slug, struggled=struggled)

async def generate_novel_problem_with_ai(
    track: str = "General",
    topic: str = "Arrays & Hash Maps",
    difficulty: str = "Medium"
) -> Dict[str, Any]:
    """
    Synthesizes a completely novel, unreleased coding problem using Gemini.
    """
    llm = get_llm(temperature=0.7)
    
    prompt = """You are a Principal Staff Engineer at a top tier tech company ({track} track).
Generate a completely original, high-quality coding problem.

Topic: {topic}
Difficulty: {difficulty}

Requirements:
1. Problem Title and rich HTML description.
2. Starter code for Python, C++ (including <bits/stdc++.h>), JavaScript, and Java.
3. 2 Sample test cases with input and expected_output JSON.
4. 2 Hidden edge-case test cases.
5. 2 Calibrated hints.

Return strictly valid JSON matching this schema:
{{
    "id": "unique_snake_case_id",
    "title": "Problem Title",
    "difficulty": "{difficulty}",
    "category": "{topic}",
    "html": "<h2 class='problemTitle'>Title</h2><div class='problemText'><p>Description</p><h3>Example 1:</h3><div class='sampleBox'>nums = [1,2], target = 3<br><strong>Output:</strong> 3</div></div>",
    "starter_code": {{
        "python": "class Solution:\\n    def solve(self, nums):\\n        return 0",
        "cpp": "#include <bits/stdc++.h>\\nusing namespace std;\\nclass Solution {\\npublic:\\n    int solve(vector<int>& nums) {\\n        return 0;\\n    }\\n};",
        "javascript": "function solve(nums) {\\n    return 0;\\n}",
        "java": "import java.util.*;\\nclass Solution {\\n    public int solve(int[] nums) {\\n        return 0;\\n    }\\n}"
    }},
    "sample_test_cases": [
        {{"name": "Example 1", "input": "{{\\"nums\\": [1, 2]}}", "input_display": "nums = [1, 2]", "expected_output": "0"}}
    ],
    "hidden_test_cases": [
        {{"name": "Edge Case 1", "input": "{{\\"nums\\": []}}", "input_display": "nums = []", "expected_output": "0"}}
    ],
    "hints": [
        {{"level": 1, "text": "Hint 1"}},
        {{"level": 2, "text": "Hint 2"}}
    ],
    "followups": [
        "Followup constraint 1"
    ]
}}
""".format(track=track, topic=topic, difficulty=difficulty)
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are an expert technical interviewer problem creator. Output ONLY JSON."),
            HumanMessage(content=prompt)
        ])
        clean_text = response.content.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        parsed = json.loads(clean_text)
        parsed["track"] = [track.lower(), "general"]
        return parsed
    except Exception as e:
        print(f"Failed to generate novel problem via AI: {e}")
        return PROBLEMS["longest_substring"]
