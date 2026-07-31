import asyncio
import os
from dotenv import load_dotenv
from agent.graph import execute_agent_turn
from agent.state import InterviewState
from problems_db import PROBLEMS

load_dotenv()

async def run_test():
    print("=== Testing LangGraph Agent ===")
    
    # Turn 1: Intro
    state: InterviewState = {
        "session_id": "test-session-123",
        "candidate_name": "Alex",
        "track": "google",
        "track_name": "Google Software Engineer (L4/L5)",
        "resume_summary": "Distributed systems and algorithmic problem solving",
        "messages": [],
        "current_phase": "Intro",
        "current_problem": PROBLEMS["two_sum"],
        "active_problem_id": "two_sum",
        "editor_code": "",
        "language": "python",
        "hints_history": []
    }
    
    res1 = await execute_agent_turn(state)
    print("\n[Turn 1 - Intro]:", res1.get("spoken_response"))
    print("Phase:", res1.get("current_phase"))
    
    # Turn 2: User responds with intro
    state["messages"].append({"role": "user", "content": "Hi Sanjay! I am Alex, I have 3 years of experience with Python and backend microservices."})
    state["current_phase"] = res1.get("current_phase", "Intro")
    res2 = await execute_agent_turn(state)
    print("\n[Turn 2 - Problem 1 Intro]:", res2.get("spoken_response"))
    print("Phase:", res2.get("current_phase"))
    
    # Turn 3: User suggests wrong data structure / brute force
    state["messages"].append({"role": "user", "content": "I am thinking of using nested loops to check every possible pair."})
    state["current_phase"] = res2.get("current_phase", "P1 Approach")
    res3 = await execute_agent_turn(state)
    print("\n[Turn 3 - Directional Nudge]:", res3.get("spoken_response"))
    print("Phase:", res3.get("current_phase"))
    
    # Turn 4: User suggests optimal Hash Map approach
    state["messages"].append({"role": "user", "content": "We can use a Hash Map to store numbers and indices in O(N) time and O(N) space."})
    state["current_phase"] = res3.get("current_phase", "P1 Approach")
    res4 = await execute_agent_turn(state)
    print("\n[Turn 4 - Optimal Approach Approved & Coding Invited]:", res4.get("spoken_response"))
    print("Phase:", res4.get("current_phase"), "| Editor Unlocked:", res4.get("editor_unlocked"))
    
    # Turn 5: Code submitted with 100% tests
    state["editor_code"] = "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        seen = {}\n        for i, n in enumerate(nums):\n            if target - n in seen:\n                return [seen[target - n], i]\n            seen[n] = i\n        return []"
    state["test_results"] = {"all_passed": True, "total_passed": 4, "total_tests": 4}
    state["messages"].append({"role": "user", "content": "I have implemented the code and all test cases passed!"})
    state["current_phase"] = "P1 Coding"
    res5 = await execute_agent_turn(state)
    print("\n[Turn 5 - Big-O Complexity Probed]:", res5.get("spoken_response"))
    print("Phase:", res5.get("current_phase"))

    # Turn 6: Complexity explained & Adaptive Q2 chosen
    state["messages"].append({"role": "user", "content": "The time complexity is O(N) because we traverse the array once, and space complexity is O(N) for the dictionary."})
    state["current_phase"] = "P1 Complexity"
    state["q1_stats"] = {"passed": 4, "total": 4}
    res6 = await execute_agent_turn(state)
    print("\n[Turn 6 - Adaptive Q2 Selected]:", res6.get("spoken_response"))
    print("Phase:", res6.get("current_phase"))
    print("Selected Adaptive Q2:", res6.get("current_problem", {}).get("title"), "(Difficulty:", res6.get("current_problem", {}).get("difficulty"), ")")

if __name__ == "__main__":
    asyncio.run(run_test())
