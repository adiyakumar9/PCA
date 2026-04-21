"""
tasks.py — Six broken Python functions covering distinct bug patterns.
Variety matters: the experiment needs different error types to surface
calibration patterns across difficulty levels.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Task:
    task_id:         str
    description:     str
    broken_function: str
    test_code:       str
    error_type:      str
    complexity:      str  # low | medium | high


TASKS: List[Task] = [

    # ── 1. Off-by-one in range ─────────────────────────────────────────────
    Task(
        task_id="task_001",
        description="Sum of list — off-by-one skips last element",
        error_type="off_by_one",
        complexity="low",
        broken_function='''\
def sum_list(numbers):
    """Return the sum of all numbers in the list."""
    total = 0
    for i in range(len(numbers) - 1):  # BUG: skips the last element
        total += numbers[i]
    return total''',
        test_code='''\
def test_sum_list():
    assert sum_list([1, 2, 3, 4, 5]) == 15
    assert sum_list([10]) == 10
    assert sum_list([]) == 0
    assert sum_list([-1, -2, 3]) == 0''',
    ),

    # ── 2. Wrong method on string ──────────────────────────────────────────
    Task(
        task_id="task_002",
        description="Palindrome check — str.reverse() doesn't exist",
        error_type="wrong_method",
        complexity="low",
        broken_function='''\
def is_palindrome(s):
    """Return True if s is a palindrome (case-insensitive)."""
    s = s.lower()
    return s == s.reverse()  # BUG: str has no .reverse(); use s[::-1]''',
        test_code='''\
def test_is_palindrome():
    assert is_palindrome("racecar") is True
    assert is_palindrome("Racecar") is True
    assert is_palindrome("hello")   is False
    assert is_palindrome("A")       is True
    assert is_palindrome("")        is True''',
    ),

    # ── 3. Wrong condition order (FizzBuzz) ────────────────────────────────
    Task(
        task_id="task_003",
        description="FizzBuzz — divisible-by-15 branch is unreachable",
        error_type="logic_error",
        complexity="medium",
        broken_function='''\
def fizzbuzz(n):
    """Return FizzBuzz list for 1..n."""
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0:        # BUG: catches multiples of 15 before the FizzBuzz branch
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        elif i % 15 == 0:     # BUG: unreachable — already caught above
            result.append("FizzBuzz")
        else:
            result.append(str(i))
    return result''',
        test_code='''\
def test_fizzbuzz():
    result = fizzbuzz(15)
    assert result[0]  == "1"
    assert result[2]  == "Fizz"
    assert result[4]  == "Buzz"
    assert result[14] == "FizzBuzz"
    assert len(result) == 15''',
    ),

    # ── 4. Operator precedence bug ─────────────────────────────────────────
    Task(
        task_id="task_004",
        description="Binary search — wrong mid calculation due to precedence",
        error_type="operator_error",
        complexity="medium",
        broken_function='''\
def binary_search(arr, target):
    """Return index of target in sorted arr, -1 if not found."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + right // 2  # BUG: should be (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1''',
        test_code='''\
def test_binary_search():
    arr = [1, 3, 5, 7, 9, 11, 13]
    assert binary_search(arr, 7)  == 3
    assert binary_search(arr, 1)  == 0
    assert binary_search(arr, 13) == 6
    assert binary_search(arr, 4)  == -1
    assert binary_search([], 5)   == -1''',
    ),

    # ── 5. Missing edge case (case sensitivity) ────────────────────────────
    Task(
        task_id="task_005",
        description="Count vowels — misses uppercase letters",
        error_type="missing_edge_case",
        complexity="low",
        broken_function='''\
def count_vowels(text):
    """Count vowels in text (case-insensitive)."""
    vowels = "aeiou"  # BUG: missing uppercase; should normalise with .lower()
    count = 0
    for char in text:
        if char in vowels:
            count += 1
    return count''',
        test_code='''\
def test_count_vowels():
    assert count_vowels("hello")       == 2
    assert count_vowels("HELLO")       == 2
    assert count_vowels("Hello World") == 3
    assert count_vowels("")            == 0
    assert count_vowels("rhythm")      == 0''',
    ),

    # ── 6. Shallow instead of deep recursion ──────────────────────────────
    Task(
        task_id="task_006",
        description="Flatten nested list — only goes one level deep",
        error_type="logic_error",
        complexity="medium",
        broken_function='''\
def flatten(lst):
    """Flatten a nested list of any depth into a flat list."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(item)  # BUG: extend doesn't recurse; need flatten(item)
        else:
            result.append(item)
    return result''',
        test_code='''\
def test_flatten():
    assert flatten([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]
    assert flatten([1, 2, 3])                 == [1, 2, 3]
    assert flatten([[1, [2]], [3]])            == [1, 2, 3]
    assert flatten([])                         == []''',
    ),

    # ── 8. HARD: Trie Prefix Search ───────────────────────────────────────
    Task(
        task_id="task_008",
        description="Trie prefix search — fails to correctly navigate node children",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False

def starts_with(root, prefix):
    """Return True if there is any word in the trie that starts with prefix."""
    curr = root
    for char in prefix:
        if char not in curr.children:
            return False
        # BUG: Missing the step to actually move to the next node
        # curr = curr.children[char] 
    return True''',
        test_code='''\
def test_starts_with():
    root = TrieNode()
    # Manual trie build for 'apple'
    curr = root
    for char in 'apple':
        curr.children[char] = TrieNode()
        curr = curr.children[char]
    curr.is_word = True
    
    assert starts_with(root, "app") is True
    assert starts_with(root, "apple") is True
    assert starts_with(root, "apply") is False
    assert starts_with(root, "b") is False''',
    ),

    # ── 9. HARD: Circular Buffer ──────────────────────────────────────────
    Task(
        task_id="task_009",
        description="Circular Buffer — wrong wrap-around logic in enqueue",
        error_type="off_by_one",
        complexity="high",
        broken_function='''\
class CircularBuffer:
    def __init__(self, size):
        self.buffer = [None] * size
        self.size = size
        self.head = 0
        self.tail = 0
        self.count = 0

    def enqueue(self, item):
        if self.count == self.size:
            return False
        self.buffer[self.tail] = item
        # BUG: Fails to wrap around correctly
        self.tail += 1 
        self.count += 1
        return True''',
        test_code='''\
def test_circular_buffer():
    cb = CircularBuffer(3)
    assert cb.enqueue(1) is True
    assert cb.enqueue(2) is True
    assert cb.enqueue(3) is True
    assert cb.enqueue(4) is False
    # If it wrapped correctly, tail should be 0 now
    assert cb.tail == 0 or cb.buffer[0] == 1''',
    ),

    # ── 11. IMPOSSIBLE: Complex State Machine ─────────────────────────────
    Task(
        task_id="task_011",
        description="State machine — wrong transition logic for nested events",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
class Parser:
    def __init__(self):
        self.state = "INIT"
        self.depth = 0

    def feed(self, char):
        if self.state == "INIT":
            if char == "{":
                self.state = "DATA"
                self.depth += 1
        elif self.state == "DATA":
            if char == "{":
                self.depth += 1
            elif char == "}":
                self.depth -= 1
                if self.depth == 0:
                    self.state = "INIT"
                # BUG: Fails to transition back to INIT when depth is 0
                # which causes it to miss trailing data or mis-parse next blocks
                pass
        return self.state''',
        test_code='''\
def test_parser():
    p = Parser()
    # Correct transitions: INIT --{--> DATA --}--> INIT
    assert p.feed("{") == "DATA"
    assert p.feed("}") == "INIT"
    assert p.feed("{") == "DATA"''',
    ),

    # ── 13. IMPOSSIBLE: Weighted Random Selection ────────────────────────
    Task(
        task_id="task_013",
        description="Weighted choice — wrong cumulative sum logic",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
import random

def weighted_choice(choices):
    """
    choices is a list of (item, weight) tuples.
    Returns an item based on its weight.
    """
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        # BUG: The logic should add w to upto and THEN compare
        if upto + w > r:
            return c
        # upto += w
    return choices[-1][0]''',
        test_code='''\
def test_weighted_choice():
    choices = [("a", 1), ("b", 100)]
    results = [weighted_choice(choices) for _ in range(100)]
    # 'b' should appear way more often than 'a'
    assert results.count("b") > 80''',
    ),

    # ── 14. IMPOSSIBLE: Interval Intersection ─────────────────────────────
    Task(
        task_id="task_014",
        description="Interval merge — fails to handle multi-interval overlaps",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
def merge_intervals(intervals):
    """Merge overlapping intervals."""
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for curr in intervals[1:]:
        prev = merged[-1]
        if curr[0] <= prev[1]:
            # BUG: Should be max(prev[1], curr[1])
            merged[-1] = (prev[0], curr[1])
        else:
            merged.append(curr)
    return merged''',
        test_code='''\
def test_merge_intervals():
    assert merge_intervals([(1, 5), (2, 4)]) == [(1, 5)]
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]
    assert merge_intervals([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]''',
    ),

    # ── 15. EXTREME: Graph Cycle with Path Tracking ───────────────────────
    Task(
        task_id="task_015",
        description="Graph pathfinder — fails to handle cycles in recursion",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
def find_all_paths(graph, start, end, path=None):
    """Find all paths from start to end in a directed graph."""
    if path is None:
        path = []
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    for node in graph[start]:
        newpaths = find_all_paths(graph, node, end, path)
        for p in newpaths:
            paths.append(p)
    return paths''',
        test_code='''\
def test_find_paths():
    graph = {'A': ['B', 'C'], 'B': ['A'], 'C': []}
    assert find_all_paths(graph, 'A', 'C') == [['A', 'C']]''',
    ),

    # ── 16. EXTREME: Multi-level Decorator State ──────────────────────────
    Task(
        task_id="task_016",
        description="Rate limiter decorator — leaks state across instances",
        error_type="logic_error",
        complexity="high",
        broken_function='''\
import time

def rate_limit(calls, period):
    """Decorator that limits a function to X calls per Y seconds."""
    timestamps = []
    def decorator(func):
        def wrapper(*args, **kwargs):
            now = time.time()
            if len(timestamps) >= calls:
                return False
            timestamps.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator''',
        test_code='''\
def test_rate_limit():
    @rate_limit(1, 100)
    def f1(): return True
    @rate_limit(1, 100)
    def f2(): return True
    assert f1() is True
    assert f1() is False
    assert f2() is True''',
    ),
]


def get_all_tasks() -> List[Task]:
    return TASKS


def get_task(task_id: str) -> Task:
    for t in TASKS:
        if t.task_id == task_id:
            return t
    raise ValueError(f"Unknown task_id: {task_id!r}")
