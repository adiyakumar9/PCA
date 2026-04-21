"""
test_runner_smoke.py — Verify the runner works before committing API credits.

Runs the test suite against the CORRECT (fixed) versions of the first two tasks.
All tests should pass. If they don't, your Python + pytest setup needs fixing.

Usage:
    python test_runner_smoke.py
"""

from runner import run_tests
from tasks import get_all_tasks


FIXED_VERSIONS = {
    "task_001": '''\
def sum_list(numbers):
    total = 0
    for i in range(len(numbers)):
        total += numbers[i]
    return total''',

    "task_002": '''\
def is_palindrome(s):
    s = s.lower()
    return s == s[::-1]''',

    "task_003": '''\
def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result''',
}


def main():
    tasks = {t.task_id: t for t in get_all_tasks()}
    passed = 0
    failed = 0

    print("Smoke test — verifying runner against known-correct fixes\n")

    for task_id, fixed_fn in FIXED_VERSIONS.items():
        task = tasks[task_id]
        result = run_tests(fixed_fn, task.test_code)
        status = "PASS" if result.success else "FAIL"
        print(f"  {task_id}: {status}  "
              f"({result.tests_passed} passed, {result.tests_failed} failed)")
        if not result.success:
            print(f"         {result.error_message}")
            failed += 1
        else:
            passed += 1

    print(f"\n  {passed}/{passed+failed} smoke tests passed")

    if failed:
        print("\n  Something is wrong with your runner setup.")
        print("  Check: is pytest installed? `pip install pytest`")
    else:
        print("\n  Runner is working correctly. Ready to run `python loop.py`.")


if __name__ == "__main__":
    main()
