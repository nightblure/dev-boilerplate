from datetime import datetime, timezone, date


def datetime_to_utc(d: datetime) -> datetime:
    return d.astimezone(tz=timezone.utc)


def date_to_datetime(d: date, *, to_utc: bool = False) -> datetime:
    dtime = datetime(
        year=d.year,
        month=d.month,
        day=d.day
    )

    if to_utc:
        dtime = datetime_to_utc(dtime)

    return dtime


def get_utc_now(format=True):
    utc_now = datetime.now(tz=timezone.utc)
    if format:
        utc_now = utc_now.strftime('%Y-%m-%d %H:%M:%S')
    return utc_now


def date_to_iso_datetime(d: date, *, to_utc: bool = True) -> str:
    d_datetime = date_to_datetime(d, to_utc=to_utc)
    d_iso = d_datetime.isoformat()
    return d_iso
