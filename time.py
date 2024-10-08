from datetime import UTC, date, datetime


def datetime_to_utc(d: datetime) -> datetime:
    return d.astimezone(tz=UTC)


def date_to_datetime(d: date, *, utc: bool = False) -> datetime:
    dtime = datetime(year=d.year, month=d.month, day=d.day)

    if utc:
        dtime = datetime_to_utc(dtime)

    return dtime


def get_utc_now() -> datetime:
    return datetime.now(tz=UTC)


def datetime_to_string(dt: datetime, *, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    return dt.strftime(fmt)


def datetime_to_rus_str_format(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y %H:%M:%S')


def create_datetime_from_string(
    dt_str: str,
    *,
    fmt: str = '%Y-%m-%d %H:%M:%S',
) -> datetime:
    return datetime.strptime(dt_str, fmt)


def date_to_iso_datetime(d: date, *, utc: bool = True) -> str:
    d_datetime = date_to_datetime(d, utc=utc)
    d_iso = d_datetime.isoformat()
    return d_iso


def unix_timestamp_from_datetime(dt: datetime) -> int:
    return int(dt.strftime('%s'))


def datetime_from_unix_timestamp(unix_timestamp: int, *, utc: bool = True) -> datetime:
    tz = None

    if utc:
        tz = UTC

    return datetime.fromtimestamp(unix_timestamp, tz=tz)
