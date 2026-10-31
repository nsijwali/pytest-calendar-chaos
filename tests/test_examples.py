import shutil
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_buggy_example_fails_on_month_end_and_reports(pytester: pytest.Pytester) -> None:
    for name in ("billing.py", "test_billing.py"):
        shutil.copy(EXAMPLES / name, pytester.path / name)
    result = pytester.runpytest()
    out = result.stdout.str()
    # Jan 31 -> replace(month=2) is invalid; Dec 31 -> month=13 is invalid.
    assert result.ret != 0
    assert "month-end-jan-31-2027" in out
    assert "Calendar chaos" in out
    assert "Reproduce: pytest 'test_billing.py::test_next_renewal_is_one_month_later[" in out
    result.assert_outcomes(
        failed=result.parseoutcomes()["failed"], passed=result.parseoutcomes()["passed"]
    )
    assert result.parseoutcomes()["failed"] >= 2
