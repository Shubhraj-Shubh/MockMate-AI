import subprocess
import tempfile
import os
import time
import requests
import json
from typing import Any, Dict, List, Optional

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

LANGUAGE_CONFIG = {
    "python": {
        "piston_lang": "python",
        "piston_version": "3.10.0",
        "file_ext": ".py"
    },
    "cpp": {
        "piston_lang": "cpp",
        "piston_version": "10.2.0",
        "file_ext": ".cpp"
    },
    "javascript": {
        "piston_lang": "javascript",
        "piston_version": "18.15.0",
        "file_ext": ".js"
    },
    "java": {
        "piston_lang": "java",
        "piston_version": "15.0.2",
        "file_ext": ".java"
    }
}

def execute_code_piston(language: str, code: str, stdin: str = "", timeout_ms: int = 3000) -> dict:
    """Executes code via the free Piston API with local subprocess fallback."""
    cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["python"])
    
    payload = {
        "language": cfg["piston_lang"],
        "version": cfg["piston_version"],
        "files": [{"content": code}],
        "stdin": stdin,
        "run_timeout": timeout_ms
    }
    
    try:
        start_time = time.time()
        res = requests.post(PISTON_URL, json=payload, timeout=4)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if res.status_code == 200:
            data = res.json()
            run_data = data.get("run", {})
            return {
                "success": run_data.get("code", 0) == 0,
                "stdout": run_data.get("stdout", "").strip(),
                "stderr": run_data.get("stderr", "").strip(),
                "output": run_data.get("output", "").strip(),
                "exit_code": run_data.get("code", 0),
                "execution_time_ms": elapsed_ms,
                "source": "piston"
            }
    except Exception as e:
        print(f"Piston API fallback to local: {e}")
        
    return execute_code_local(language, code, stdin)

def execute_code_local(language: str, code: str, stdin: str = "") -> dict:
    """Fallback local subprocess execution (Python, C++, Node.js)."""
    cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["python"])
    start_time = time.time()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = "Main" + cfg["file_ext"] if language == "java" else "main" + cfg["file_ext"]
        filepath = os.path.join(tmpdir, filename)
        
        with open(filepath, "w") as f:
            f.write(code)
            
        try:
            if language == "python":
                proc = subprocess.run(
                    ["python3", filepath],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=4
                )
            elif language == "cpp":
                include_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "include")
                bin_path = os.path.join(tmpdir, "out")
                compile_proc = subprocess.run(
                    ["g++", "-std=c++17", f"-I{include_dir}", filepath, "-o", bin_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if compile_proc.returncode != 0:
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": compile_proc.stderr,
                        "output": compile_proc.stderr,
                        "exit_code": compile_proc.returncode,
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                        "source": "local"
                    }
                proc = subprocess.run(
                    [bin_path],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=3
                )
            elif language == "javascript":
                proc = subprocess.run(
                    ["node", filepath],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=4
                )
            elif language == "java":
                compile_proc = subprocess.run(
                    ["javac", filepath],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if compile_proc.returncode != 0:
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": compile_proc.stderr,
                        "output": compile_proc.stderr,
                        "exit_code": compile_proc.returncode,
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                        "source": "local"
                    }
                proc = subprocess.run(
                    ["java", "-cp", tmpdir, "Main"],
                    input=stdin,
                    text=True,
                    capture_output=True,
                    timeout=3
                )
            else:
                return {"success": False, "stderr": f"Unsupported language: {language}"}
                
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "output": (proc.stdout + proc.stderr).strip(),
                "exit_code": proc.returncode,
                "execution_time_ms": elapsed_ms,
                "source": "local"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Execution timed out (Time Limit Exceeded - 3.0s)",
                "output": "Time Limit Exceeded",
                "exit_code": -1,
                "execution_time_ms": 3000,
                "source": "local"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "output": str(e),
                "exit_code": -1,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "source": "local"
            }

def to_cpp_literal(val: Any) -> str:
    """Converts a Python data structure to a C++ initializer literal."""
    if val is None:
        return "nullptr"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            return "{}"
        inner = ", ".join(to_cpp_literal(x) for x in val)
        return f"{{{inner}}}"
    if isinstance(val, dict):
        return "{}"
    return str(val)

def to_cpp_var(idx: int, val: Any) -> tuple[str, str]:
    """Generates a C++ variable declaration and its variable name for argument passing."""
    var_name = f"arg_{idx}"
    if isinstance(val, bool):
        return f"bool {var_name} = {'true' if val else 'false'};", var_name
    elif isinstance(val, int):
        t = "int" if abs(val) <= 2147483647 else "long long"
        return f"{t} {var_name} = {val};", var_name
    elif isinstance(val, float):
        return f"double {var_name} = {val};", var_name
    elif isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'string {var_name} = "{escaped}";', var_name
    elif isinstance(val, list):
        if not val:
            return f"vector<int> {var_name} = {{}};", var_name
        first = val[0]
        if isinstance(first, list):
            sub_first = first[0] if first else 0
            if isinstance(sub_first, str):
                inner = ", ".join(f"{{{', '.join(to_cpp_literal(x) for x in sub)}}}" for sub in val)
                return f"vector<vector<string>> {var_name} = {{{inner}}};", var_name
            elif isinstance(sub_first, bool):
                inner = ", ".join(f"{{{', '.join(to_cpp_literal(x) for x in sub)}}}" for sub in val)
                return f"vector<vector<bool>> {var_name} = {{{inner}}};", var_name
            else:
                inner = ", ".join(f"{{{', '.join(to_cpp_literal(x) for x in sub)}}}" for sub in val)
                return f"vector<vector<int>> {var_name} = {{{inner}}};", var_name
        elif isinstance(first, str):
            inner = ", ".join(to_cpp_literal(x) for x in val)
            return f"vector<string> {var_name} = {{{inner}}};", var_name
        elif isinstance(first, bool):
            inner = ", ".join(to_cpp_literal(x) for x in val)
            return f"vector<bool> {var_name} = {{{inner}}};", var_name
        else:
            inner = ", ".join(to_cpp_literal(x) for x in val)
            return f"vector<int> {var_name} = {{{inner}}};", var_name
    return f"auto {var_name} = {val};", var_name

def to_java_literal(val: Any) -> str:
    """Converts a Python data structure to a Java typed allocation expression."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val}f" if abs(val) < 1e6 else str(val)
    if isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            return "new int[]{}"
        first = val[0]
        if isinstance(first, list):
            sub_first = first[0] if first else 0
            if isinstance(sub_first, str):
                inner = ", ".join(f"new String[]{{{', '.join(to_java_literal(x) for x in sub)}}}" for sub in val)
                return f"new String[][]{{{inner}}}"
            elif isinstance(sub_first, bool):
                inner = ", ".join(f"new boolean[]{{{', '.join(to_java_literal(x) for x in sub)}}}" for sub in val)
                return f"new boolean[][]{{{inner}}}"
            else:
                inner = ", ".join(f"new int[]{{{', '.join(to_java_literal(x) for x in sub)}}}" for sub in val)
                return f"new int[][]{{{inner}}}"
        elif isinstance(first, str):
            inner = ", ".join(to_java_literal(x) for x in val)
            return f"new String[]{{{inner}}}"
        elif isinstance(first, bool):
            inner = ", ".join(to_java_literal(x) for x in val)
            return f"new boolean[]{{{inner}}}"
        else:
            inner = ", ".join(to_java_literal(x) for x in val)
            return f"new int[]{{{inner}}}"
    return str(val)

def build_test_runner_code(language: str, user_code: str, test_case: dict, problem_id: str) -> str:
    """Wraps user code with a 100% generic dynamic test harness for test case execution across Python, C++, JS, and Java."""
    from leetcode_client import get_problem
    prob = get_problem(problem_id)
    func_name = prob.get("function_name", "solve") if prob else "solve"

    raw_input = test_case.get("input", "{}")
    data = {}
    try:
        data = json.loads(raw_input)
    except Exception:
        pass

    if language == "python":
        return f"""{user_code}

import json

try:
    data = json.loads('''{raw_input}''')
    sol = Solution()
    func = getattr(sol, '{func_name}', None)
    if func is None:
        methods = [m for m in dir(sol) if callable(getattr(sol, m)) and not m.startswith('_')]
        func = getattr(sol, methods[0]) if methods else None
        
    if func is None:
        print("Error: No solution method found on Solution class")
    else:
        if isinstance(data, dict):
            try:
                res = func(**data)
            except TypeError:
                res = func(*data.values())
        elif isinstance(data, list):
            res = func(*data)
        else:
            res = func(data)
            
        if isinstance(res, (list, tuple, dict, bool)) or res is None:
            print(json.dumps(res))
        else:
            print(res)
except Exception as e:
    print(f"Runtime Error: {{e}}")
"""

    elif language == "javascript":
        return f"""{user_code}

try {{
    const data = {raw_input if raw_input else '{}'};
    let res;
    let fn = (typeof {func_name} === 'function') ? {func_name} : null;
    let ctx = null;
    
    if (!fn && typeof Solution === 'function') {{
        ctx = new Solution();
        fn = ctx.{func_name} || Object.getOwnPropertyNames(Object.getPrototypeOf(ctx)).filter(m => m !== 'constructor' && typeof ctx[m] === 'function').map(m => ctx[m])[0];
    }}
    
    if (!fn) {{
        console.log("Error: Function {func_name} not found");
        process.exit(0);
    }}
    
    const args = (typeof data === 'object' && !Array.isArray(data) && data !== null) ? Object.values(data) : (Array.isArray(data) ? data : [data]);
    res = fn.apply(ctx, args);
    console.log(JSON.stringify(res));
}} catch (e) {{
    console.log("Runtime Error: " + e.message);
}}
"""

    elif language == "cpp":
        args_list = list(data.values()) if isinstance(data, dict) else (data if isinstance(data, list) else [data])
        decls = []
        names = []
        for i, v in enumerate(args_list):
            decl, name = to_cpp_var(i, v)
            decls.append(f"        {decl}")
            names.append(name)
        decls_code = "\n".join(decls)
        cpp_args = ", ".join(names)
        return f"""#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <stack>
#include <deque>
#include <set>
#include <map>
#include <sstream>
#include <cmath>
using namespace std;

{user_code}

template<typename T>
void print_val(const T& val) {{ cout << val; }}

inline void print_val(bool val) {{ cout << (val ? "true" : "false"); }}
inline void print_val(const string& val) {{ cout << "\\"" << val << "\\""; }}

template<typename T>
void print_val(const vector<T>& vec) {{
    cout << "[";
    for (size_t i = 0; i < vec.size(); ++i) {{
        print_val(vec[i]);
        if (i + 1 < vec.size()) cout << ",";
    }}
    cout << "]";
}}

int main() {{
    try {{
        Solution sol;
{decls_code}
        auto res = sol.{func_name}({cpp_args});
        print_val(res);
        cout << endl;
    }} catch (const exception& e) {{
        cout << "Runtime Error: " << e.what() << endl;
    }}
    return 0;
}}
"""

    elif language == "java":
        args_list = list(data.values()) if isinstance(data, dict) else (data if isinstance(data, list) else [data])
        java_args = ", ".join(to_java_literal(v) for v in args_list)
        return f"""import java.util.*;

{user_code}

class Main {{
    private static void printResult(Object obj) {{
        if (obj == null) {{
            System.out.println("null");
        }} else if (obj instanceof int[]) {{
            System.out.println(Arrays.toString((int[]) obj));
        }} else if (obj instanceof long[]) {{
            System.out.println(Arrays.toString((long[]) obj));
        }} else if (obj instanceof double[]) {{
            System.out.println(Arrays.toString((double[]) obj));
        }} else if (obj instanceof boolean[]) {{
            System.out.println(Arrays.toString((boolean[]) obj));
        }} else if (obj instanceof char[]) {{
            System.out.println(Arrays.toString((char[]) obj));
        }} else if (obj instanceof Object[]) {{
            System.out.println(Arrays.deepToString((Object[]) obj));
        }} else if (obj instanceof List) {{
            System.out.println(obj.toString());
        }} else {{
            System.out.println(obj);
        }}
    }}

    public static void main(String[] args) {{
        try {{
            Solution sol = new Solution();
            var res = sol.{func_name}({java_args});
            printResult(res);
        }} catch (Exception e) {{
            System.out.println("Runtime Error: " + e.getMessage());
        }}
    }}
}}
"""

    return user_code

def is_solution_correct(actual_str: str, expected_str: str, problem_id: str) -> bool:
    """Accurately compares actual and expected test case results."""
    actual_str = actual_str.strip()
    expected_str = expected_str.strip()
    
    if not actual_str or not expected_str:
        return False
        
    if actual_str == expected_str:
        return True
        
    # JSON comparison
    try:
        act_val = json.loads(actual_str)
        exp_val = json.loads(expected_str)
        
        if act_val == exp_val:
            return True
            
        # Group Anagrams / 3Sum / Nested lists (order independent)
        if isinstance(act_val, list) and isinstance(exp_val, list):
            if all(isinstance(x, list) for x in act_val) and all(isinstance(x, list) for x in exp_val):
                sorted_act = sorted([sorted([str(i) for i in sub]) for sub in act_val])
                sorted_exp = sorted([sorted([str(i) for i in sub]) for sub in exp_val])
                if sorted_act == sorted_exp:
                    return True
            elif sorted([str(x) for x in act_val]) == sorted([str(x) for x in exp_val]):
                return True
    except Exception:
        pass
        
    # Float comparison
    try:
        if abs(float(actual_str) - float(expected_str)) < 1e-4:
            return True
    except Exception:
        pass
        
    # Integer comparison
    try:
        return int(actual_str) == int(expected_str)
    except Exception:
        pass
        
    # Clean whitespace comparison
    clean_act = "".join(actual_str.split())
    clean_exp = "".join(expected_str.split())
    return clean_act == clean_exp

def evaluate_test_cases(language: str, user_code: str, test_cases: list, problem_id: str) -> dict:
    """Runs and verifies multiple test cases."""
    results = []
    total_passed = 0
    
    for idx, tc in enumerate(test_cases):
        test_code = build_test_runner_code(language, user_code, tc, problem_id)
        exec_res = execute_code_piston(language, test_code, stdin=tc.get("stdin", ""))
        
        # Take the last line of stdout if there are debug prints
        raw_stdout = exec_res["stdout"].strip()
        actual_output = raw_stdout.splitlines()[-1].strip() if raw_stdout else ""
        expected_output = str(tc.get("expected_output", "")).strip()
        
        passed = is_solution_correct(actual_output, expected_output, problem_id)
            
        if passed:
            total_passed += 1
            
        results.append({
            "test_id": idx + 1,
            "name": tc.get("name", f"Test Case {idx + 1}"),
            "input": tc.get("input_display", tc.get("input", "")),
            "expected_output": expected_output,
            "actual_output": actual_output if exec_res["success"] else (exec_res["stderr"] or "Runtime Error"),
            "passed": passed,
            "execution_time_ms": exec_res["execution_time_ms"],
            "error": exec_res["stderr"] if not exec_res["success"] else None
        })
        
    return {
        "total_tests": len(test_cases),
        "total_passed": total_passed,
        "all_passed": total_passed == len(test_cases) and len(test_cases) > 0,
        "results": results
    }
