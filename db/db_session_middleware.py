from starlette.middleware.base import BaseHTTPMiddleware

from db.deps import get_db_session_context


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            with get_db_session_context() as db_session:
                request.state.db = db_session
                response = await call_next(request)
        except Exception as e:
            raise e from None
        finally:
            request.state.db.close()

        return response
