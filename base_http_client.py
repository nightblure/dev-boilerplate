import asyncio
from typing import Any

import httpx
from loguru import logger
from requests import Response

from some_project.exceptions import ExternalServiceError, ExternalServiceTimeoutError, PixiError
from decorators import log_if_errors


class SomeServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code


class ExternalServiceError(SomeServiceError):
    status_code = 500

    def __init__(self, host_or_svc_name: str):
        super().__init__(
            f'External service "{host_or_svc_name}" unavailable', self.status_code
        )


class ExternalServiceTimeoutError(SomeServiceError):
    status_code = 500

    def __init__(self, host_or_svc_name: str):
        super().__init__(f'Timeout error while connecting to "{host_or_svc_name}"', self.status_code)


class Result:
    def __init__(self, response: Response):
        self.response = response
        self.status_code = response.status_code

        try:
            self.content: dict[str, Any] = response.json()
            self.is_json = True
        except ValueError:
            self.content: dict[str, Any] = {'text': response.text}
            self.is_json = False

        self.ok = 200 <= response.status_code < 300
        self.client_error = 400 <= response.status_code < 500
        self.server_error = 500 <= response.status_code < 600


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
            auth_endpoint: str | None = None
    ):
        self.host = host.rstrip('/')
        self.api_version = api_version.lstrip('/')
        self.app_name = app_name

        self.user = user
        self.password = password
        self.auth_endpoint = auth_endpoint

        self.default_headers = {
            'User-Agent': app_name,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.token = None

    def make_url(self, endpoint: str):
        if self.api_version == '':
            url = f"{self.host}/{endpoint.lstrip('/')}"
        else:
            url = f"{self.host}/{self.api_version.lstrip('/')}/{endpoint.lstrip('/')}"
        return url

    @log_if_errors()
    async def request(
            self,
            method: str,
            *,
            endpoint: str,
            query_params: dict[str, Any] | None = None,
            body: dict[str, Any] = None,
            headers=None,
            timeout: int = TIMEOUT,
            retries: int = 1,
            retries_timeout: int = RETRIES_TIMEOUT,
            follow_redirects=False
    ) -> Result:
        url = self.make_url(endpoint)

        if headers is None:
            headers = {}

        headers = {**self.default_headers, **headers}
        current_retries_timeout = retries_timeout
        current_backoff = 1

        for i in range(retries):
            try:
                result = await self._send_request(
                    method,
                    url=url,
                    query_params=query_params,
                    body=body,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=follow_redirects
                )

                if result.ok:
                    return result

            # We SHOULDN'T to retry client errors (4XX)
            except (ExternalServiceError, ExternalServiceTimeoutError) as e:
                if retries == 1:
                    raise e

                current_retries_timeout = round(current_retries_timeout * current_backoff, 2)
                logger.warning(
                    f'Make retry №{i + 1} to host {self.host}, '
                    f'sleep for {current_retries_timeout} seconds...'
                )
                await asyncio.sleep(current_retries_timeout)
                current_backoff *= self.RETRIES_BACKOFF_FACTOR
                continue

        raise ExternalServiceError(self.host)

    async def _send_request(
            self,
            method: str,
            *,
            url: str,
            query_params: dict[str, Any] | None = None,
            body: dict[str, Any] = None,
            headers=None,
            timeout: int,
            follow_redirects=False
    ):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method.upper(),
                    url=url,
                    params=query_params,
                    headers=headers,
                    json=body,
                    timeout=timeout,
                    follow_redirects=follow_redirects
                )

                if response.is_success:
                    return Result(response)

                if response.is_client_error:
                    msg = (
                        f'Client error while connecting to "{self.host}". '
                        f'Content: {response.content}; status code: {response.status_code}'
                    )
                    logger.error(msg)
                    # Client error here is same as internal error
                    raise PixiError(msg)

                if response.is_server_error:
                    logger.error(f'Internal server error on "{self.host}: {str(response.content)}"')
                    raise ExternalServiceError(self.host)

        except httpx.TimeoutException:
            msg = f'Timeout error while connecting to "{self.host}"'
            logger.exception(msg)
            raise ExternalServiceTimeoutError(self.host)

    async def get(self, **kw):
        """See available arguments in request method"""
        return await self.request('get', **kw)

    async def post(self, **kw):
        """See available arguments in request method"""
        return await self.request('post', **kw)

    async def put(self, **kw):
        """See available arguments in request method"""
        return await self.request('put', **kw)

