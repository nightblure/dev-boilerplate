import asyncio
from typing import Any

import httpx
from loguru import logger


class ExternalServiceError(Exception):
    status_code = 500
    _message = 'Internal server error'

    def __init__(
        self,
        host: str,
        *,
        message: str | None = None,
        status_code: int | None = None,
    ):
        if message is not None:
            self._message = message

        super().__init__(host)

        if status_code is None:
            status_code = self.status_code

        self.host = host
        self.status_code = status_code

    @property
    def log_message(self) -> str:
        return (
            f'Error while connecting to {self.host!r}.\n'
            f'Reason: {self.message}.\n'
            f'Status code: {self.status_code}'
        )

    @property
    def message(self) -> str:
        return self._message

    def __repr__(self):
        return (
            f'{self.__class__.__name__}('
            f'host={self.host!r}, '
            f'message={self.message!r}',
            f'log_message={self.log_message!r}',
            ')',
        )

    def __str__(self):
        return self.message


class ExternalServiceTimeoutError(ExternalServiceError):
    status_code = 504

    @property
    def message(self) -> str:
        return f'Timeout error while connecting to host {self.host!r}'


class ExternalServiceUnknownError(ExternalServiceError):
    @property
    def message(self) -> str:
        return f'Unknown error while connecting to host {self.host!r}'


class Result:
    def __init__(self, response: httpx.Response):
        self.response = response
        self.status_code = response.status_code

        try:
            self.content: dict[str, Any] = response.json()
            self.is_json = True
        except ValueError:
            self.content: dict[str, Any] = {'text': response.text}
            self.is_json = False

        self.text = response.text
        self.ok = 200 <= response.status_code < 300
        self.client_error = 400 <= response.status_code <= 499
        self.server_error = 500 <= response.status_code <= 599
        self.host = f'{response.url.scheme}://{response.url.host}'

    def __repr__(self):
        return f'Result(status_code={self.status_code}, host={self.host!r})'


def _raise_for_status(result: Result):
    raise ExternalServiceError(
        host=result.host,
        message=result.text,
        status_code=result.status_code,
    )


class BaseHttpClient:
    RETRIES_TIMEOUT = 1
    RETRIES_BACKOFF_FACTOR = 1.15
    TIMEOUT = 5

    def __init__(
        self,
        *,
        host: str,
        api_version: str = '',
        app_name: str,
        user: str | None = None,
        password: str | None = None,
        auth_endpoint: str | None = None,
    ):
        self.host = host.rstrip('/')
        self.api_version = api_version.lstrip('/')
        self.app_name = app_name

        self.user = user
        self.password = password
        self.auth_endpoint = auth_endpoint

        self._default_request_headers = {
            'User-Agent': app_name,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def make_url(self, endpoint: str):
        if self.api_version == '':
            url = f"{self.host}/{endpoint.lstrip('/')}"
        else:
            url = f"{self.host}/{self.api_version.lstrip('/')}/{endpoint.lstrip('/')}"
        return url

    async def request(
        self,
        method: str,
        *,
        endpoint: str,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        timeout: int = TIMEOUT,
        retries: int = 1,
        retries_timeout: int = RETRIES_TIMEOUT,
        follow_redirects=False,
        raise_for_status: bool = True,
    ) -> Result:
        url = self.make_url(endpoint)

        if headers is None:
            headers = {}

        headers = {**self._default_request_headers, **headers}
        current_retries_timeout = retries_timeout
        current_backoff = 1

        for i in range(retries):
            try:
                result = await self.__send_request(
                    method,
                    url=url,
                    query_params=query_params,
                    body=body,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                    raise_for_status=raise_for_status,
                )

                return result

            except ExternalServiceError as e:
                # We SHOULDN'T to retry client errors (4XX)
                if 400 <= e.status_code < 500:
                    raise

                if retries == 1:
                    raise

                current_retries_timeout = round(
                    current_retries_timeout * current_backoff,
                    2,
                )
                logger.warning(
                    f'Make retry №{i + 1} to host {self.host}, '
                    f'sleep for {current_retries_timeout} seconds...',
                )
                await asyncio.sleep(current_retries_timeout)
                current_backoff *= self.RETRIES_BACKOFF_FACTOR
                continue
            except Exception as e:
                raise ExternalServiceError(host=self.host, message=str(e)) from e

        raise ExternalServiceUnknownError(host=self.host)

    async def __send_request(
        self,
        method: str,
        *,
        url: str,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers=None,
        timeout: int,
        follow_redirects=False,
        raise_for_status: bool = True,
    ) -> Result:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method.upper(),
                    url=url,
                    params=query_params,
                    headers=headers,
                    json=body,
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                )

                result = Result(response)

                if response.is_success or not raise_for_status:
                    return result

                _raise_for_status(result)

        except httpx.TimeoutException as e:
            raise ExternalServiceTimeoutError(host=self.host) from e

    async def get(self, **kw) -> Result:
        """See available arguments in request method"""
        return await self.request('get', **kw)

    async def post(self, **kw) -> Result:
        """See available arguments in request method"""
        return await self.request('post', **kw)

    async def put(self, **kw) -> Result:
        """See available arguments in request method"""
        return await self.request('put', **kw)
