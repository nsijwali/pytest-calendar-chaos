from datetime import datetime

import pytest
from billing import next_renewal


@pytest.mark.calendar_chaos(cases=["month_end", "year_end"])
def test_next_renewal_is_one_month_later():
    created_at = datetime.now()
    renewal = next_renewal(created_at)
    assert renewal > created_at
    assert renewal.day <= created_at.day
