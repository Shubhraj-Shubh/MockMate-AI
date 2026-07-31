import random
from typing import Dict, Any, List, Tuple, Optional
from leetcode_client import get_problem

# Minimalist curated LeetCode problem slugs grouped by difficulty
PROBLEMS_BY_DIFFICULTY = {
    "medium": [
        # --- Arrays, Hashing & Matrices ---
        "group-anagrams",
        "top-k-frequent-elements",
        "product-of-array-except-self",
        "valid-sudoku",
        "encode-and-decode-strings",
        "longest-consecutive-sequence",
        "sort-colors",
        "subarray-sum-equals-k",
        "rotate-image",
        "spiral-matrix",
        "set-matrix-zeroes",
        "game-of-life",
        "increasing-triplet-subsequence",
        "contiguous-array",
        "find-all-anagrams-in-a-string",
        "grid-game",
        "maximum-subarray",
        "maximum-product-subarray",
        "insert-delete-getrandom-o1",
        "h-index",
        "gas-station",
        "majority-element-ii",
        "find-the-duplicate-number",
        "continuous-subarray-sum",
        "range-sum-query-2d-immutable",

        # --- Two Pointers & Sliding Window ---
        "two-sum-ii-input-array-is-sorted",
        "3sum",
        "3sum-closest",
        "4sum",
        "container-with-most-water",
        "rotate-array",
        "boats-to-save-people",
        "partition-labels",
        "bag-of-tokens",
        "minimize-maximum-pair-sum-in-array",
        "valid-triangle-number",
        "number-of-subsequences-that-satisfy-the-given-sum-condition",
        "string-compression",
        "push-dominoes",
        "move-pieces-to-obtain-a-string",
        "heaters",
        "k-diff-pairs-in-an-array",
        "count-number-of-nice-subarrays",
        "longest-substring-without-repeating-characters",
        "longest-repeating-character-replacement",
        "permutation-in-string",
        "minimum-size-subarray-sum",
        "fruit-into-baskets",
        "maximum-number-of-vowels-in-a-substring-of-given-length",
        "grumpy-bookstore-owner",
        "maximum-points-you-can-obtain-from-cards",
        "frequency-of-the-most-frequent-element",
        "max-consecutive-ones-iii",
        "get-equal-substrings-within-budget",
        "number-of-substrings-containing-all-three-characters",
        "binary-subarrays-with-sum",
        "find-the-longest-equal-subarray",
        "maximum-erasure-value",
        "minimum-operations-to-reduce-x-to-zero",
        "continuous-subarrays",
        "take-k-of-each-character-from-left-and-right",

        # --- Stack & Monotonic Stack ---
        "min-stack",
        "evaluate-reverse-polish-notation",
        "generate-parentheses",
        "daily-temperatures",
        "car-fleet",
        "online-stock-span",
        "simplify-path",
        "decode-string",
        "remove-k-digits",
        "132-pattern",
        "asteroid-collision",
        "next-greater-element-ii",
        "sum-of-subarray-minimums",
        "remove-all-adjacent-duplicates-in-string-ii",
        "validate-stack-sequences",
        "minimum-add-to-make-parentheses-valid",
        "score-of-parentheses",
        "basic-calculator-ii",
        "flatten-nested-list-iterator",
        "design-a-stack-with-increment-operation",

        # --- Binary Search ---
        "search-in-rotated-sorted-array",
        "search-in-rotated-sorted-array-ii",
        "find-minimum-in-rotated-sorted-array",
        "search-a-2d-matrix",
        "search-a-2d-matrix-ii",
        "koko-eating-bananas",
        "capacity-to-ship-packages-within-d-days",
        "time-based-key-value-store",
        "find-peak-element",
        "single-element-in-a-sorted-array",
        "find-first-and-last-position-of-element-in-sorted-array",
        "minimum-limit-of-balls-in-a-bag",
        "magnetic-force-between-two-balls",
        "maximum-candies-allocated-to-k-children",
        "snapshot-array",
        "peak-index-in-a-mountain-array",
        "find-right-interval",
        "kth-smallest-element-in-a-sorted-matrix",
        "ugly-number-iii",
        "minimum-speed-to-arrive-on-time",

        # --- Linked List ---
        "add-two-numbers",
        "linked-list-cycle-ii",
        "reorder-list",
        "remove-nth-node-from-end-of-list",
        "copy-list-with-random-pointer",
        "lru-cache",
        "reverse-linked-list-ii",
        "sort-list",
        "partition-list",
        "rotate-list",
        "swap-nodes-in-pairs",
        "odd-even-linked-list",
        "remove-duplicates-from-sorted-list-ii",
        "flatten-a-multilevel-doubly-linked-list",
        "design-browser-history",
        "split-linked-list-in-parts",
        "swapping-nodes-in-a-linked-list",
        "insertion-sort-list",
        "linked-list-random-node",
        "design-linked-list",

        # --- Trees & Binary Search Trees ---
        "lowest-common-ancestor-of-a-binary-search-tree",
        "lowest-common-ancestor-of-a-binary-tree",
        "binary-tree-level-order-traversal",
        "binary-tree-zigzag-level-order-traversal",
        "binary-tree-right-side-view",
        "count-good-nodes-in-binary-tree",
        "validate-binary-search-tree",
        "kth-smallest-element-in-a-bst",
        "construct-binary-tree-from-preorder-and-inorder-traversal",
        "construct-binary-tree-from-inorder-and-postorder-traversal",
        "populating-next-right-pointers-in-each-node",
        "populating-next-right-pointers-in-each-node-ii",
        "flatten-binary-tree-to-linked-list",
        "path-sum-ii",
        "path-sum-iii",
        "sum-root-to-leaf-numbers",
        "binary-search-tree-iterator",
        "delete-node-in-a-bst",
        "insert-into-a-binary-search-tree",
        "house-robber-iii",
        "trim-a-binary-search-tree",
        "all-nodes-distance-k-in-binary-tree",
        "maximum-width-of-binary-tree",
        "step-by-step-directions-from-a-binary-tree-node-to-another",
        "flip-equivalent-binary-trees",

        # --- Heap / Priority Queue & Trie ---
        "kth-largest-element-in-an-array",
        "top-k-frequent-words",
        "task-scheduler",
        "design-twitter",
        "find-k-pairs-with-smallest-sums",
        "reorganize-string",
        "k-closest-points-to-origin",
        "seat-reservation-manager",
        "process-tasks-using-servers",
        "single-threaded-cpu",
        "implement-trie-prefix-tree",
        "design-add-and-search-words-data-structure",
        "extra-characters-in-a-string",
        "replace-words",
        "map-sum-pairs",

        # --- Backtracking ---
        "subsets",
        "subsets-ii",
        "combination-sum",
        "combination-sum-ii",
        "combination-sum-iii",
        "permutations",
        "permutations-ii",
        "word-search",
        "letter-combinations-of-a-phone-number",
        "palindrome-partitioning",
        "restore-ip-addresses",
        "matchsticks-to-fire",
        "partition-to-k-equal-sum-subsets",
        "non-decreasing-subsequences",
        "fair-distribution-of-cookies",

        # --- Graphs & Disjoint Set Union ---
        "number-of-islands",
        "max-area-of-island",
        "clone-graph",
        "surrounded-regions",
        "pacific-atlantic-water-flow",
        "course-schedule",
        "course-schedule-ii",
        "redundant-connection",
        "evaluate-division",
        "accounts-merge",
        "word-ladder",
        "snakes-and-ladders",
        "open-the-lock",
        "minimum-height-trees",
        "network-delay-time",
        "cheapest-flights-within-k-stops",
        "is-graph-bipartite",
        "path-with-maximum-effort",
        "find-eventual-safe-states",
        "as-far-from-land-as-possible",
        "rotting-oranges",
        "shortest-path-in-binary-matrix",
        "number-of-provinces",
        "keys-and-rooms",
        "reorder-routes-to-make-all-paths-lead-to-the-city-zero",

        # --- 1D & Dynamic Programming ---
        "house-robber",
        "house-robber-ii",
        "longest-palindromic-substring",
        "palindromic-substrings",
        "decode-ways",
        "coin-change",
        "word-break",
        "longest-increasing-subsequence",
        "partition-equal-subset-sum",
        "integer-break",
        "combination-sum-iv",
        "perfect-squares",
        "coin-change-ii",
        "target-sum",
        "domino-and-tromino-tiling",
        "uncrossed-lines",
        "solving-questions-with-brainpower",
        "count-number-of-texts",
        "number-of-dice-rolls-with-target-sum",
        "push-dominoes",

        # --- 2D Dynamic Programming, Greedy & Intervals ---
        "unique-paths",
        "unique-paths-ii",
        "minimum-path-sum",
        "longest-common-subsequence",
        "best-time-to-buy-and-sell-stock-with-cooldown",
        "best-time-to-buy-and-sell-stock-with-transaction-fee",
        "interleaving-string",
        "maximal-square",
        "merge-intervals",
        "insert-interval",
        "non-overlapping-intervals",
        "minimum-number-of-arrows-to-burst-balloons",
        "jump-game",
        "jump-game-ii",
        "hand-of-straights",
        "dota2-senate",
        "single-number-ii",
        "powx-n",
        "multiply-strings",
        "counter-ii",
        "find-polygon-with-the-largest-perimeter",
        "minimum-deletions-to-make-character-frequencies-unique",
        "maximum-element-after-decreasing-and-rearranging",
        "furthest-building-you-can-reach",
        "find-the-minimum-and-maximum-number-of-nodes-between-critical-points",
        "delete-nodes-from-linked-list-present-in-array",
        "nodes-between-critical-points",
        "spiral-matrix-iv",
        "insert-greatest-common-divisors-in-linked-list",
        "find-the-prefix-common-array-of-two-arrays"
    ],
    "hard": [
        # --- Arrays, Two Pointers & Sliding Window ---
        "trapping-rain-water",
        "median-of-two-sorted-arrays",
        "sliding-window-maximum",
        "minimum-window-substring",
        "first-missing-positive",
        "substring-with-concatenation-of-all-words",
        "smallest-range-covering-elements-from-k-lists",
        "max-points-on-a-line",
        "orderly-queue",
        "count-subarrays-with-score-less-than-k",

        # --- Stack, Queue & Design ---
        "largest-rectangle-in-histogram",
        "basic-calculator",
        "maximum-frequency-stack",
        "lfu-cache",
        "insert-delete-getrandom-o1-duplicates-allowed",
        "all-o-one-data-structure",
        "number-of-atoms",
        "parse-lisp-expression",

        # --- Linked List, Trees & Tries ---
        "merge-k-sorted-lists",
        "reverse-nodes-in-k-group",
        "serialize-and-deserialize-binary-tree",
        "binary-tree-maximum-path-sum",
        "word-search-ii",
        "prefix-and-suffix-search",
        "sum-of-distances-in-tree",

        # --- Heap & Priority Queue ---
        "find-median-from-data-stream",
        "minimum-cost-to-hire-k-workers",
        "ipo",
        "minimum-number-of-refueling-stops",
        "meeting-rooms-iii",

        # --- Graph, BFS/DFS & Topological Sort ---
        "word-ladder-ii",
        "alien-dictionary",
        "reconstruct-itinerary",
        "swim-in-rising-water",
        "trapping-rain-water-ii",
        "shortest-path-in-a-grid-with-obstacles-elimination",
        "sliding-puzzle",
        "cut-off-trees-for-golf-event",
        "redundant-connection-ii",
        "cracking-the-safe",
        "couples-holding-hands",
        "bricks-falling-when-hit",
        "making-a-large-island",
        "shortest-path-visiting-all-nodes",
        "guess-the-word",
        "critical-connections-in-a-network",
        "minimum-moves-to-reach-target-with-rotations",
        "minimum-cost-to-make-at-least-one-valid-path-in-a-grid",
        "frog-position-after-t-seconds",
        "last-day-where-you-can-still-cross",

        # --- Backtracking & Search ---
        "n-queens",
        "sudoku-solver",
        "remove-invalid-parentheses",
        "expression-add-operators",

        # --- Dynamic Programming & Strings ---
        "regular-expression-matching",
        "wildcard-matching",
        "longest-valid-parentheses",
        "edit-distance",
        "burst-balloons",
        "cherry-pickup",
        "cherry-pickup-ii",
        "dungeon-game",
        "palindromic-partitioning-ii",
        "word-break-ii",
        "distinct-subsequences",
        "concatenated-words",
        "russian-doll-envelopes",
        "minimum-insertion-steps-to-make-a-string-palindrome",
        "frog-jump",
        "split-array-largest-sum",
        "freedom-trail",
        "student-attendance-record-ii",
        "strange-printer",
        "maximal-rectangle",
        "race-car",
        "stamping-the-sequence",
        "find-the-shortest-superstring",
        "tallest-billboard",
        "minimum-cost-to-merge-stones",
        "number-of-squareful-arrays",
        "shortest-common-supersequence",
        "maximum-profit-in-job-scheduling",
        "minimum-falling-path-sum-ii",
        "minimum-distance-to-type-a-word-using-two-fingers",
        "jump-game-iv",
        "count-all-valid-pickup-and-delivery-options",
        "paint-house-iii",
        "parallel-courses-iii",
        "k-th-smallest-in-lexicographical-order",
        "text-justification",
        "skyline-problem",
        "falling-squares",
        "vowel-spellchecker",
        "triples-with-bitwise-and-equal-to-zero",
        "grid-illumination",
        "find-in-mountain-array",
        "find-minimum-in-rotated-sorted-array-ii",
        "k-similar-strings"
    ]
}

# 3-Tier Interview System Configuration
INTERVIEW_TIERS = {
    "easy": {
        "id": "easy",
        "name": "Easy Tier (2 Medium Questions)",
        "description": "Standard 1-hour software engineering interview focusing on fundamental data structures and algorithmic patterns.",
        "default_q1": "medium",
        "default_q2": "medium",
        "duration_minutes": 60
    },
    "medium": {
        "id": "medium",
        "name": "Medium Tier (1 Medium + 1 Hard)",
        "description": "Mid-to-Senior 1-hour interview covering optimization, edge cases, and advanced algorithmic design.",
        "default_q1": "medium",
        "default_q2": "hard",
        "duration_minutes": 60
    },
    "hard": {
        "name": "Hard Tier (2 Hard Questions)",
        "id": "hard",
        "description": "Staff/Principal 1-hour interview testing complex data structures, multi-pass algorithms, and scaling trade-offs.",
        "default_q1": "hard",
        "default_q2": "hard",
        "duration_minutes": 60
    },
    "cv_grill": {
        "name": "CV / Resume Grilling (25-30 min)",
        "id": "cv_grill",
        "description": "Rigorous 25-30 min deep-dive into your projects, architectural trade-offs, tech stack decisions, and failure modes.",
        "default_q1": "medium",
        "default_q2": "hard",
        "duration_minutes": 30
    }
}

# Backward compatibility alias
COMPANY_TRACKS = INTERVIEW_TIERS

class LazyProblemDict(dict):
    """Dynamically fetches problem data on access while maintaining dictionary semantics."""
    def __getitem__(self, key):
        slug = key.replace("_", "-")
        return get_problem(slug)
        
    def get(self, key, default=None):
        try:
            slug = key.replace("_", "-")
            return get_problem(slug)
        except Exception:
            return default

PROBLEMS = LazyProblemDict()
get_problem_by_id = get_problem

def get_track_problems(tier_id: str = "medium") -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Selects Question 1 and initial Question 2 for the chosen difficulty tier."""
    cfg = INTERVIEW_TIERS.get(tier_id.lower(), INTERVIEW_TIERS["medium"])
    
    if tier_id.lower() == "cv_grill":
        cv_dummy = {
            "id": "cv-grilling-session",
            "title": "Project Architecture & CV Deep-Dive",
            "difficulty": "Staff",
            "category": ["System Design", "Architecture", "Project Deep-Dive"],
            "html": "<h2 class='problemTitle'>Project Architecture & CV Deep-Dive</h2><p>In this 35-40 minute session, the AI will interrogate your projects, system architecture, scaling limits, and technical trade-offs.</p>",
            "starter_code": "// Technical Discussion & Architecture Scratchpad\n// Use this editor to write notes, architectural flows, or schema designs if needed.\n",
            "all_starter_codes": {
                "python": "# System Architecture & Notes Scratchpad\n",
                "javascript": "// System Architecture & Notes Scratchpad\n",
                "cpp": "// System Architecture & Notes Scratchpad\n",
                "java": "// System Architecture & Notes Scratchpad\n"
            },
            "sample_test_cases": []
        }
        return cv_dummy, cv_dummy, cfg
    
    q1_diff = cfg["default_q1"]
    q2_diff = cfg["default_q2"]
    
    q1_slug = random.choice(PROBLEMS_BY_DIFFICULTY[q1_diff])
    
    # Pick a distinct Q2 slug
    available_q2 = [s for s in PROBLEMS_BY_DIFFICULTY[q2_diff] if s != q1_slug]
    q2_slug = random.choice(available_q2) if available_q2 else PROBLEMS_BY_DIFFICULTY[q2_diff][0]
    
    q1 = get_problem(q1_slug)
    q2 = get_problem(q2_slug)
    
    return q1, q2, cfg

def get_adaptive_q2(tier_id: str, q1_slug: str, struggled: bool = False) -> Dict[str, Any]:
    """Dynamically chooses Question 2 based on candidate's Question 1 performance."""
    tier = tier_id.lower()
    
    if tier == "medium":
        # If candidate struggled on Q1 in Medium Tier, adaptively give another Medium instead of Hard
        target_diff = "medium" if struggled else "hard"
    elif tier == "easy":
        target_diff = "medium"
    else: # hard tier
        target_diff = "medium" if struggled else "hard"
        
    available = [s for s in PROBLEMS_BY_DIFFICULTY[target_diff] if s != q1_slug]
    selected_slug = random.choice(available) if available else PROBLEMS_BY_DIFFICULTY[target_diff][0]
    
    return get_problem(selected_slug)
