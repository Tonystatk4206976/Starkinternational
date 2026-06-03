"""Lightweight Dedalus Machines API helpers.

The official ``dedalus-sdk`` package is generated from Dedalus' OpenAPI spec and
is the most complete client.  This module provides a dependency-free facade with
method names that mirror that generated SDK, plus a few convenience helpers for
common agent workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

JsonMap = dict[str, Any]
Headers = Mapping[str, str]
Query = Mapping[str, Any]


class DedalusAPIError(RuntimeError):
    """Base error raised by the lightweight Dedalus Machines client."""


class DedalusAPIStatusError(DedalusAPIError):
    """Raised when the Dedalus API returns a non-2xx HTTP status."""

    def __init__(self, status_code: int, message: str, response: Any = None) -> None:
        super().__init__(f"Dedalus API returned HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response = response


class DedalusAPIConnectionError(DedalusAPIError):
    """Raised when a network-level connection error occurs."""


@dataclass(frozen=True)
class DedalusMachinesConfig:
    """Configuration for :class:`DedalusMachinesClient`.

    Args:
        api_key: Dedalus API key. Defaults to ``DEDALUS_API_KEY``.
        base_url: API origin. The generated SDK uses paths under ``/v1``.
        timeout: Request timeout in seconds.
        auth_header: Header used for API-key auth. Dedalus accepts bearer auth;
            use ``X-API-Key`` if your deployment requires that style.
        default_headers: Extra headers sent with every request.
    """

    api_key: str | None = None
    base_url: str = "https://api.dedaluslabs.ai"
    timeout: float = 60.0
    auth_header: str = "Authorization"
    default_headers: Mapping[str, str] = field(default_factory=dict)

    def resolved_api_key(self) -> str:
        api_key = self.api_key or os.environ.get("DEDALUS_API_KEY")
        if not api_key:
            raise ValueError("Set api_key or the DEDALUS_API_KEY environment variable")
        return api_key


class DedalusMachinesClient:
    """Dependency-free Dedalus Machines API client.

    Resource methods intentionally follow the public shape of the OpenAPI-
    generated ``dedalus-sdk`` client: ``client.machines.create(...)``,
    ``client.machines.executions.create(...)``, ``client.usage.retrieve(...)``,
    and so on. Responses are decoded JSON dictionaries/lists so callers can use
    the client without Pydantic or httpx.
    """

    def __init__(self, config: DedalusMachinesConfig | None = None, **kwargs: Any) -> None:
        self.config = config or DedalusMachinesConfig(**kwargs)
        self.machines = MachinesResource(self)
        self.usage = UsageResource(self)

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        query: Query | None = None,
        headers: Headers | None = None,
        stream: bool = False,
    ) -> Any:
        """Send a raw JSON request to the Dedalus API."""
        url = self._url(path, query=query)
        request_body = None
        request_headers: MutableMapping[str, str] = {
            "Accept": "text/event-stream" if stream else "application/json",
            "User-Agent": "Starkinternational-DedalusMachines/1.0",
            **self.config.default_headers,
            **(headers or {}),
        }
        api_key = self.config.resolved_api_key()
        if self.config.auth_header.lower() == "authorization":
            request_headers[self.config.auth_header] = f"Bearer {api_key}"
        else:
            request_headers[self.config.auth_header] = api_key

        if body is not None:
            request_body = json.dumps(_strip_missing(body)).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        request = Request(url, data=request_body, headers=dict(request_headers), method=method.upper())
        try:
            response = urlopen(request, timeout=self.config.timeout)
        except HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise DedalusAPIStatusError(exc.code, payload or exc.reason, _maybe_json(payload)) from exc
        except URLError as exc:
            raise DedalusAPIConnectionError(str(exc.reason)) from exc

        if stream:
            return response

        payload = response.read().decode("utf-8")
        if not payload:
            return None
        return json.loads(payload)

    def iter_sse(
        self,
        path: str,
        *,
        query: Query | None = None,
        headers: Headers | None = None,
    ) -> Iterator[JsonMap]:
        """Yield Server-Sent Event objects from a streaming API endpoint."""
        response = self.request("GET", path, query=query, headers=headers, stream=True)
        event: JsonMap = {"event": "message", "data": ""}
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if not line:
                if event.get("data"):
                    event["data"] = _maybe_json(str(event["data"]).rstrip("\n"))
                    yield event
                event = {"event": "message", "data": ""}
                continue
            if line.startswith(":"):
                continue
            field_name, _, value = line.partition(":")
            if value.startswith(" "):
                value = value[1:]
            if field_name == "data":
                event["data"] = f"{event.get('data', '')}{value}\n"
            elif field_name in {"event", "id", "retry"}:
                event[field_name] = value

    def _url(self, path: str, *, query: Query | None = None) -> str:
        base = self.config.base_url.rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        filtered_query = _strip_missing(query or {})
        if filtered_query:
            return f"{base}{normalized_path}?{urlencode(filtered_query, doseq=True)}"
        return f"{base}{normalized_path}"


class MachinesResource:
    """Machine lifecycle resource."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client
        self.artifacts = ArtifactsResource(client)
        self.previews = PreviewsResource(client)
        self.ssh = SSHResource(client)
        self.executions = ExecutionsResource(client)
        self.terminals = TerminalsResource(client)

    def create(
        self,
        *,
        memory_mib: int,
        storage_gib: int,
        vcpu: float,
        autosleep: str | None = None,
        idempotency_key: str | None = None,
    ) -> JsonMap:
        headers = _idempotency_headers(idempotency_key)
        return self._client.request(
            "POST",
            "/v1/machines",
            body={"memory_mib": memory_mib, "storage_gib": storage_gib, "vcpu": vcpu, "autosleep": autosleep},
            headers=headers,
        )

    def retrieve(self, *, machine_id: str) -> JsonMap:
        return self._client.request("GET", _machine_path(machine_id))

    def update(
        self,
        *,
        machine_id: str,
        autosleep: str | None = None,
        memory_mib: int | None = None,
        storage_gib: int | None = None,
        vcpu: float | None = None,
        idempotency_key: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "PATCH",
            _machine_path(machine_id),
            body={"autosleep": autosleep, "memory_mib": memory_mib, "storage_gib": storage_gib, "vcpu": vcpu},
            headers=_idempotency_headers(idempotency_key),
        )

    def list(self, *, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", "/v1/machines", query={"cursor": cursor, "limit": limit})

    def iter_all(self, *, limit: int = 100) -> Iterator[JsonMap]:
        yield from _paginate(lambda cursor: self.list(cursor=cursor, limit=limit))

    def delete(self, *, machine_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _machine_path(machine_id), headers=_idempotency_headers(idempotency_key))

    def sleep(self, *, machine_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("POST", f"{_machine_path(machine_id)}/sleep", headers=_idempotency_headers(idempotency_key))

    def wake(self, *, machine_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("POST", f"{_machine_path(machine_id)}/wake", headers=_idempotency_headers(idempotency_key))

    def watch(self, *, machine_id: str, last_event_id: str | None = None) -> Iterator[JsonMap]:
        headers = {"Last-Event-ID": last_event_id} if last_event_id else None
        return self._client.iter_sse(f"{_machine_path(machine_id)}/status/stream", headers=headers)

    def wait_for_phase(
        self,
        *,
        machine_id: str,
        phase: str = "running",
        timeout_s: float = 120.0,
        poll_interval_s: float = 2.0,
    ) -> JsonMap:
        """Poll a machine until ``status.phase`` reaches ``phase``."""
        deadline = time.monotonic() + timeout_s
        while True:
            machine = self.retrieve(machine_id=machine_id)
            if _phase(machine) == phase:
                return machine
            if time.monotonic() >= deadline:
                raise TimeoutError(f"machine {machine_id} did not reach phase {phase!r} before timeout")
            time.sleep(poll_interval_s)


class ExecutionsResource:
    """Execution resource for running non-interactive commands."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def create(
        self,
        *,
        machine_id: str,
        command: Sequence[str] | None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "POST",
            f"{_machine_path(machine_id)}/executions",
            body={"command": list(command) if command is not None else None, "cwd": cwd, "env": env, "stdin": stdin, "timeout_ms": timeout_ms},
            headers=_idempotency_headers(idempotency_key),
        )

    def retrieve(self, *, machine_id: str, execution_id: str) -> JsonMap:
        return self._client.request("GET", _execution_path(machine_id, execution_id))

    def list(self, *, machine_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_machine_path(machine_id)}/executions", query={"cursor": cursor, "limit": limit})

    def iter_all(self, *, machine_id: str, limit: int = 100) -> Iterator[JsonMap]:
        yield from _paginate(lambda cursor: self.list(machine_id=machine_id, cursor=cursor, limit=limit))

    def delete(self, *, machine_id: str, execution_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _execution_path(machine_id, execution_id), headers=_idempotency_headers(idempotency_key))

    def events(self, *, machine_id: str, execution_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_execution_path(machine_id, execution_id)}/events", query={"cursor": cursor, "limit": limit})

    def output(self, *, machine_id: str, execution_id: str) -> JsonMap:
        return self._client.request("GET", f"{_execution_path(machine_id, execution_id)}/output")

    def run_and_wait(
        self,
        *,
        machine_id: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
        timeout_ms: int | None = None,
        poll_interval_s: float = 1.0,
        terminal_phases: set[str] | None = None,
    ) -> JsonMap:
        """Create an execution, poll it to completion, and attach output."""
        execution = self.create(
            machine_id=machine_id,
            command=command,
            cwd=cwd,
            env=env,
            stdin=stdin,
            timeout_ms=timeout_ms,
        )
        execution_id = _extract_id(execution, "execution_id", "id")
        terminal = terminal_phases or {"succeeded", "failed", "cancelled", "canceled", "timed_out"}
        while _phase(execution) not in terminal:
            time.sleep(poll_interval_s)
            execution = self.retrieve(machine_id=machine_id, execution_id=execution_id)
        execution["output"] = self.output(machine_id=machine_id, execution_id=execution_id)
        return execution


class PreviewsResource:
    """Port preview resource for exposing machine services over HTTPS."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def create(
        self,
        *,
        machine_id: str,
        port: int,
        protocol: str | None = None,
        visibility: str | None = None,
        idempotency_key: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "POST",
            f"{_machine_path(machine_id)}/previews",
            body={"port": port, "protocol": protocol, "visibility": visibility},
            headers=_idempotency_headers(idempotency_key),
        )

    def retrieve(self, *, machine_id: str, preview_id: str) -> JsonMap:
        return self._client.request("GET", _nested_path(machine_id, "previews", preview_id))

    def list(self, *, machine_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_machine_path(machine_id)}/previews", query={"cursor": cursor, "limit": limit})

    def delete(self, *, machine_id: str, preview_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _nested_path(machine_id, "previews", preview_id), headers=_idempotency_headers(idempotency_key))


class SSHResource:
    """SSH session resource."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def create(self, *, machine_id: str, public_key: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request(
            "POST",
            f"{_machine_path(machine_id)}/ssh",
            body={"public_key": public_key},
            headers=_idempotency_headers(idempotency_key),
        )

    def retrieve(self, *, machine_id: str, session_id: str) -> JsonMap:
        return self._client.request("GET", _nested_path(machine_id, "ssh", session_id))

    def list(self, *, machine_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_machine_path(machine_id)}/ssh", query={"cursor": cursor, "limit": limit})

    def delete(self, *, machine_id: str, session_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _nested_path(machine_id, "ssh", session_id), headers=_idempotency_headers(idempotency_key))


class TerminalsResource:
    """Terminal resource for creating PTY sessions."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def create(
        self,
        *,
        machine_id: str,
        height: int,
        width: int,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        shell: str | None = None,
        idempotency_key: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "POST",
            f"{_machine_path(machine_id)}/terminals",
            body={"height": height, "width": width, "cwd": cwd, "env": env, "shell": shell},
            headers=_idempotency_headers(idempotency_key),
        )

    def retrieve(self, *, machine_id: str, terminal_id: str) -> JsonMap:
        return self._client.request("GET", _nested_path(machine_id, "terminals", terminal_id))

    def list(self, *, machine_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_machine_path(machine_id)}/terminals", query={"cursor": cursor, "limit": limit})

    def delete(self, *, machine_id: str, terminal_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _nested_path(machine_id, "terminals", terminal_id), headers=_idempotency_headers(idempotency_key))


class ArtifactsResource:
    """Execution artifact resource."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def retrieve(self, *, machine_id: str, artifact_id: str) -> JsonMap:
        return self._client.request("GET", _nested_path(machine_id, "artifacts", artifact_id))

    def list(self, *, machine_id: str, cursor: str | None = None, limit: int | None = None) -> JsonMap:
        return self._client.request("GET", f"{_machine_path(machine_id)}/artifacts", query={"cursor": cursor, "limit": limit})

    def delete(self, *, machine_id: str, artifact_id: str, idempotency_key: str | None = None) -> JsonMap:
        return self._client.request("DELETE", _nested_path(machine_id, "artifacts", artifact_id), headers=_idempotency_headers(idempotency_key))


class UsageResource:
    """Usage summary and machine usage breakdown resource."""

    def __init__(self, client: DedalusMachinesClient) -> None:
        self._client = client

    def retrieve(self, *, period_start: str | None = None) -> JsonMap:
        return self._client.request("GET", "/v1/usage", query={"period_start": period_start})

    def machine_compute(
        self,
        *,
        granularity: str | None = None,
        machine_id: str | None = None,
        period_end: str | None = None,
        period_start: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "GET",
            "/v1/usage/machines/compute",
            query={"granularity": granularity, "machine_id": machine_id, "period_end": period_end, "period_start": period_start},
        )

    def machine_storage(
        self,
        *,
        machine_id: str | None = None,
        period_end: str | None = None,
        period_start: str | None = None,
    ) -> JsonMap:
        return self._client.request(
            "GET",
            "/v1/usage/machines/storage",
            query={"machine_id": machine_id, "period_end": period_end, "period_start": period_start},
        )


class GeneratedDedalusMachines:
    """Thin wrapper around an installed OpenAPI-generated ``dedalus-sdk`` client.

    Pass an official ``dedalus_sdk.Dedalus`` instance to expose the same resource
    attributes as this module while retaining generated models, retries, and
    WebSocket/SSE support from the official SDK.
    """

    def __init__(self, generated_client: Any) -> None:
        self.generated_client = generated_client
        self.machines = generated_client.machines
        self.usage = generated_client.usage

    @classmethod
    def from_default_sdk(cls, **kwargs: Any) -> "GeneratedDedalusMachines":
        """Construct from ``dedalus-sdk`` if it is installed."""
        import importlib
        import importlib.util

        if importlib.util.find_spec("dedalus_sdk") is None:
            raise RuntimeError("Install the generated SDK with: pip install dedalus-sdk")
        module = importlib.import_module("dedalus_sdk")
        return cls(module.Dedalus(**kwargs))


def _strip_missing(values: Mapping[str, Any]) -> JsonMap:
    return {key: value for key, value in values.items() if value is not None}


def _maybe_json(payload: str) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def _machine_path(machine_id: str) -> str:
    _require_non_empty("machine_id", machine_id)
    return f"/v1/machines/{machine_id}"


def _execution_path(machine_id: str, execution_id: str) -> str:
    _require_non_empty("execution_id", execution_id)
    return f"{_machine_path(machine_id)}/executions/{execution_id}"


def _nested_path(machine_id: str, resource: str, resource_id: str) -> str:
    _require_non_empty(f"{resource[:-1]}_id", resource_id)
    return f"{_machine_path(machine_id)}/{resource}/{resource_id}"


def _require_non_empty(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"Expected a non-empty value for `{name}` but received {value!r}")


def _idempotency_headers(idempotency_key: str | None) -> Headers | None:
    return {"Idempotency-Key": idempotency_key} if idempotency_key else None


def _phase(payload: Mapping[str, Any]) -> str | None:
    status = payload.get("status")
    if isinstance(status, Mapping):
        value = status.get("phase") or status.get("state")
        return str(value) if value is not None else None
    for key in ("phase", "state", "status"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _extract_id(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    raise KeyError(f"Could not find any of {keys!r} in response")


def _paginate(fetch_page: Callable[[str | None], JsonMap]) -> Iterator[JsonMap]:
    cursor: str | None = None
    while True:
        page = fetch_page(cursor)
        if isinstance(page, Mapping):
            items = page.get("items", [])
            cursor = page.get("next_cursor")
        elif isinstance(page, list):
            items = page
            cursor = None
        else:
            return
        if not isinstance(items, Iterable):
            return
        for item in items:
            yield item
        if not cursor:
            return
