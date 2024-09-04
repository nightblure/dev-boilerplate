from dependency_injector import containers, providers

from .session_manager import DbSessionManager
from .uow import UnitOfWork

wiring_packages = ['..api', '..cache']


class DIContainer(containers.DeclarativeContainer):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # BEFORE START APP WE NEED TO EXPLICIT CALL DIContainer.wire() METHOD!
    wiring_config = containers.WiringConfiguration(
        packages=wiring_packages,
        auto_wire=False,
    )
    settings = providers.Singleton(SomeSettings)

    db_session_manager = providers.Singleton(
        DbSessionManager,
        db_url=settings.provided.database,
        echo=settings.provided.sqla_echo,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        scoped=False,
    )

    uow = providers.Factory(UnitOfWork, db_session_manager=db_session_manager)



di_container = DIContainer.instance()
