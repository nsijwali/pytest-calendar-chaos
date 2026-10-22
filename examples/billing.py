from datetime import datetime


def next_renewal(created_at: datetime) -> datetime:
    """Return the same day next month. Deliberately buggy: breaks at month end."""
    return created_at.replace(month=created_at.month + 1)
