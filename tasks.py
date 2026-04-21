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

]


def get_all_tasks() -> List[Task]:
    return TASKS


def get_task(task_id: str) -> Task:
    for t in TASKS:
        if t.task_id == task_id:
            return t
    raise ValueError(f"Unknown task_id: {task_id!r}")
