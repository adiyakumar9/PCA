"""
runner.py — Write fixed code + tests to a temp file, run pytest, return results.
No imports from the rest of the system — keeps this module independently testable.
"""

import sys
import re
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass


@dataclass
class TestResult:
    success:          bool
    tests_passed:     int
    tests_failed:     int
    error_message:    str | None
    execution_time_ms: int


def run_tests(fixed_function: str, test_code: str, timeout: int = 20) -> TestResult:
    """
    Combine fixed_function + test_code into one file, run pytest, return structured result.

    The combined file layout:
        <fixed_function>          ← the function under test
        <blank line>
        <test_code>               ← pytest test functions
    """
    full_source = f"{fixed_function}\n\n{test_code}\n"
    start = time.time()

    # Write to a uniquely named temp file (auto-deleted after we're done)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_test.py",
        prefix="phase1_",
        delete=False,
        dir=tempfile.gettempdir(),
    )
    try:
        tmp.write(full_source)
        tmp.flush()
        tmp.close()

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                tmp.name,
                "-v",           # verbose: one line per test
                "--tb=short",   # short traceback on failure
                "--no-header",  # skip the pytest version header
                "-q",           # quiet: suppress extra output
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        output = result.stdout + result.stderr

        # Parse "X passed / X failed / X error" from pytest summary line
        tests_passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", output)) else 0
        tests_failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", output)) else 0
        tests_failed += int(m.group(1)) if (m := re.search(r"(\d+) error",  output)) else 0

        success = (result.returncode == 0 and tests_failed == 0)

        error_message = None
        if not success:
            # Grab the most informative lines
            lines = output.split("\n")
            relevant = [l for l in lines if any(
                kw in l for kw in ("FAILED", "ERROR", "AssertionError", "assert", "E ")
            )]
            error_message = "\n".join(relevant[:8]) if relevant else output[-600:]

        return TestResult(
            success=success,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            error_message=error_message,
            execution_time_ms=elapsed_ms,
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            success=False,
            tests_passed=0,
            tests_failed=1,
            error_message=f"Timed out after {timeout}s",
            execution_time_ms=timeout * 1000,
        )
    except Exception as exc:
        return TestResult(
            success=False,
            tests_passed=0,
            tests_failed=1,
            error_message=str(exc),
            execution_time_ms=0,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
pass
