"""Decide whether a scheduled run is due and how many postings it should add.

The daily quota (search.per_day) is split evenly across schedule.run_hours. A run that happens after
earlier runs were missed (for example, the computer was asleep all day) makes up the shortfall.
"""


def quotas(run_hours, per_day):
    """Postings per run hour; any remainder goes to the earliest runs."""
    hours = sorted(run_hours)
    base, extra = divmod(per_day, len(hours))
    return {h: base + (1 if i < extra else 0) for i, h in enumerate(hours)}


def current_slot(hour, run_hours):
    """The latest run hour that has already started, or None before the first one."""
    started = [h for h in sorted(run_hours) if h <= hour]
    return started[-1] if started else None


def slot_name(run_hour):
    return f"{run_hour:02d}h"


def target(slot_hour, run_hours, per_day, done_today):
    """Postings to add in this slot: its own quota, or more if earlier slots fell short."""
    q = quotas(run_hours, per_day)
    due_total = sum(n for h, n in q.items() if h <= slot_hour)
    return max(q[slot_hour], due_total - done_today)
