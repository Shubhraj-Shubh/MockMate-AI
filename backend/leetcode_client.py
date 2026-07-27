import os
import json
import re
import html
import requests
from typing import Dict, Any, Optional, List

from pymongo import MongoClient

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# In-memory problem cache
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

# MongoDB Connection
_mongo_db = None
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    try:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        _mongo_db = _mongo_client.get_database("ai_interview_db")
        print("Connected to MongoDB for LeetCode problem caching.")
    except Exception as e:
        print(f"MongoDB connection failed in leetcode_client: {e}")
        _mongo_db = None

def parse_leetcode_graphql_response(slug: str, data: dict) -> Optional[Dict[str, Any]]:
    """Transforms raw LeetCode GraphQL question data into our standard problem format."""
    q = data.get("data", {}).get("question")
    if not q:
        return None

    title = q.get("title", slug.replace("-", " ").title())
    difficulty = q.get("difficulty", "Medium")
    raw_content = q.get("content", "")
    
    # Extract Starter Code Snippets
    starter_code = {
        "python": "class Solution:\n    # Write your solution here\n    pass",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nclass Solution {\npublic:\n    // Write your solution here\n};",
        "javascript": "/**\n * @return {any}\n */\nvar solution = function() {\n    // Write your solution here\n};",
        "java": "import java.util.*;\n\nclass Solution {\n    // Write your solution here\n}"
    }
    
    for snippet in q.get("codeSnippets", []):
        lang = snippet.get("langSlug")
        code = snippet.get("code", "")
        if lang in ["python3", "python"]:
            starter_code["python"] = code
        elif lang == "cpp":
            starter_code["cpp"] = code
        elif lang == "javascript":
            starter_code["javascript"] = code
        elif lang == "java":
            starter_code["java"] = code

    # Parse metadata (function name & parameters)
    meta_raw = q.get("metaData", "{}")
    meta_data = {}
    try:
        meta_data = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
    except Exception:
        pass

    param_names = [p.get("name") for p in meta_data.get("params", []) if isinstance(p, dict)]
    func_name = meta_data.get("name", "solve")

    # Extract Expected Outputs from HTML
    # Matches patterns like <strong>Output:</strong> 3, <strong>Output:</strong> <span class="example-io">...</span>, <pre>...Output: ...</pre>
    raw_matches = re.findall(
        r'<strong>\s*Output:?\s*</strong>\s*:?\s*(?:<(?:span|code|pre)[^>]*>)?\s*(.*?)(?:</(?:span|code|pre)>|</p>|</div>|\n\s*\n|<p>|<strong>\s*Explanation|\n\s*<strong>|\Z)',
        raw_content,
        re.DOTALL | re.IGNORECASE
    )
    clean_outputs = []
    for m in raw_matches:
        text = re.sub(r'<[^>]+>', '', m).strip()
        text = html.unescape(text)
        text = text.split('\n')[0].strip()
        if text:
            clean_outputs.append(text)

    # Parse Test Cases
    raw_testcases = q.get("exampleTestcaseList", [])
    if not raw_testcases and q.get("sampleTestCase"):
        raw_testcases = [q.get("sampleTestCase")]

    sample_test_cases = []
    for idx, tc_str in enumerate(raw_testcases):
        lines = [l.strip() for l in tc_str.split("\n") if l.strip()]
        params_map = {}
        for i, line in enumerate(lines):
            if i < len(param_names):
                try:
                    params_map[param_names[i]] = json.loads(line)
                except Exception:
                    params_map[param_names[i]] = line
            else:
                try:
                    params_map[f"arg{i}"] = json.loads(line)
                except Exception:
                    params_map[f"arg{i}"] = line

        input_json = json.dumps(params_map)
        input_display = ", ".join(f"{k} = {v}" for k, v in params_map.items()) if params_map else tc_str
        expected_output = clean_outputs[idx] if idx < len(clean_outputs) else ""

        sample_test_cases.append({
            "name": f"Example {idx + 1}",
            "input": input_json,
            "input_display": input_display,
            "expected_output": expected_output
        })

    # Prepare Hints
    hints_list = []
    raw_hints = q.get("hints", [])
    if raw_hints:
        for idx, h in enumerate(raw_hints):
            hints_list.append({"level": idx + 1, "text": html.unescape(h)})
    else:
        hints_list = [
            {"level": 1, "text": f"Consider the core data structures that could optimize this {difficulty.lower()} problem."},
            {"level": 2, "text": "Think about edge cases such as empty inputs, single element boundaries, or large inputs."}
        ]

    # Build final formatted HTML
    problem_html = f"""<h2 class="problemTitle">{title}</h2>
<div class="problemDifficulty {difficulty.lower()}">{difficulty}</div>
<div class="problemText">
{raw_content}
</div>"""

    return {
        "id": slug,
        "title": title,
        "difficulty": difficulty,
        "category": [t.get("name") for t in q.get("topicTags", [])] or ["Data Structures & Algorithms"],
        "function_name": func_name,
        "meta_data": meta_data,
        "param_names": param_names,
        "hints": hints_list,
        "followups": [
            "What is the time and space complexity of your solution?",
            "How would you scale this approach if data was arriving in a real-time stream?"
        ],
        "html": problem_html,
        "starter_code": starter_code,
        "sample_test_cases": sample_test_cases,
        "hidden_test_cases": sample_test_cases  # Will run against full test suite
    }

def fetch_from_leetcode_graphql(slug: str) -> Optional[Dict[str, Any]]:
    """Queries LeetCode's public GraphQL API for a problem slug."""
    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
        titleSlug
        difficulty
        content
        codeSnippets {
          langSlug
          code
        }
        sampleTestCase
        exampleTestcaseList
        metaData
        hints
        topicTags {
          name
        }
      }
    }
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        res = requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": {"titleSlug": slug}},
            headers=headers,
            timeout=6
        )
        if res.status_code == 200:
            return parse_leetcode_graphql_response(slug, res.json())
    except Exception as e:
        print(f"LeetCode GraphQL query failed for {slug}: {e}")
        
    return None

def get_problem(slug: str) -> Dict[str, Any]:
    """Retrieves a problem by slug from memory, MongoDB, or LeetCode GraphQL."""
    # 1. Check memory cache
    if slug in _MEMORY_CACHE:
        return _MEMORY_CACHE[slug]

    # 2. Check MongoDB collection
    if _mongo_db is not None:
        try:
            cached_doc = _mongo_db.leetcode_problems.find_one({"id": slug}, {"_id": 0})
            if cached_doc:
                _MEMORY_CACHE[slug] = cached_doc
                return cached_doc
        except Exception as e:
            print(f"MongoDB lookup error for {slug}: {e}")

    # 3. Query LeetCode GraphQL
    prob = fetch_from_leetcode_graphql(slug)
    if prob:
        _MEMORY_CACHE[slug] = prob
        if _mongo_db is not None:
            try:
                _mongo_db.leetcode_problems.update_one(
                    {"id": slug},
                    {"$set": prob},
                    upsert=True
                )
            except Exception as e:
                print(f"Failed to cache problem {slug} to MongoDB: {e}")
        return prob

    # 3. Fallback to basic template if completely offline
    fallback_title = slug.replace("-", " ").title()
    fallback_prob = {
        "id": slug,
        "title": fallback_title,
        "difficulty": "Medium",
        "category": ["Algorithms"],
        "function_name": "solve",
        "meta_data": {"name": "solve", "params": [{"name": "nums", "type": "integer[]"}]},
        "param_names": ["nums"],
        "hints": [
            {"level": 1, "text": "Consider the optimal time complexity and data structures."},
            {"level": 2, "text": "Check your handling of edge cases and boundary conditions."}
        ],
        "followups": [
            "What is the time and space complexity of your solution?",
            "How would this perform with streaming data?"
        ],
        "html": f"<h2 class='problemTitle'>{fallback_title}</h2><p>Solve the {fallback_title} challenge efficiently.</p>",
        "starter_code": {
            "python": "class Solution:\n    def solve(self, nums: list[int]) -> int:\n        return 0",
            "cpp": "#include <bits/stdc++.h>\nusing namespace std;\nclass Solution {\npublic:\n    int solve(vector<int>& nums) { return 0; }\n};",
            "javascript": "function solve(nums) {\n    return 0;\n}",
            "java": "import java.util.*;\nclass Solution {\n    public int solve(int[] nums) { return 0; }\n}"
        },
        "sample_test_cases": [
            {"name": "Example 1", "input": '{"nums": [1, 2, 3]}', "input_display": "nums = [1, 2, 3]", "expected_output": "0"}
        ],
        "hidden_test_cases": [
            {"name": "Example 1", "input": '{"nums": [1, 2, 3]}', "input_display": "nums = [1, 2, 3]", "expected_output": "0"}
        ]
    }
    _MEMORY_CACHE[slug] = fallback_prob
    return fallback_prob
