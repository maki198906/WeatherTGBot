import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


def _job_id(user_id: int) -> str:
    return f"sub_{user_id}"


def add_or_replace_job(send_fn, sub: dict) -> None:
    """Schedule or reschedule a daily weather job for one subscription."""
    hour, minute = sub["send_time"].split(":")
    try:
        tz = pytz.timezone(sub["tz"])
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc
    scheduler.add_job(
        send_fn,
        trigger=CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
        id=_job_id(sub["user_id"]),
        args=[sub["user_id"], sub["city"]],
        replace_existing=True,
        # If the laptop is asleep or network drops, don't drop the job. 
        # Run it as soon as the bot wakes up.
        misfire_grace_time=None,
    )


def remove_job(user_id: int) -> None:
    """Remove a scheduled job if it exists."""
    job_id = _job_id(user_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def start(send_fn) -> None:
    """Restore all saved subscriptions and start the scheduler."""
    from subscriptions import get_all_subscriptions
    for sub in get_all_subscriptions():
        add_or_replace_job(send_fn, sub)
    scheduler.start()
