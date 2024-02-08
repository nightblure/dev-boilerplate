settings = ProjectSettings()


def create_db_session_manager(settings: ProjectSettings = settings):
    return DbSessionManager(
        database_uri=settings.database,
        echo=False,
        scoped=False
    )


def with_session(db_session_manager=create_db_session_manager()):
    """Inject session into decorated function. Name for the session arg must be 'db_session'"""

    def wrapper(f):
        def inner(*a, **kw):
            with db_session_manager.context_session() as db_session:
                kw['db_session'] = db_session
                result = f(*a, **kw)
                return result

            # OR USE CODE BELOW
            # session = db_session_manager.get_session()
            # kw['db_session'] = session
            # result = f(*a, **kw)
            # session.close()
            # return result

        return inner

    return wrapper


@with_session()
def create_some_repository(db_session=None):
    return SomeRepository(db_session=db_session)
