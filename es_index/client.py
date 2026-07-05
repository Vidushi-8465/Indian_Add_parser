"""Elasticsearch client factory with .env support, retries, and connection testing."""

from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from loguru import logger

from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG, PROJECT_ROOT
from utils.file_utils import load_yaml_config

_es_logger = logger.bind(module="es_index.client")

# Load .env once at import time so ELASTIC_* vars are available project-wide.
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_host(config: dict[str, Any]) -> list[str]:
    """Build host URL list from .env (host + port) or YAML config."""
    env_host = os.environ.get("ELASTIC_HOST")
    env_port = os.environ.get("ELASTIC_PORT")

    if env_host:
        if env_host.startswith("http"):
            return [env_host]
        if env_port:
            return [f"http://{env_host}:{env_port}"]
        return [f"http://{env_host}:9200"]

    connection = config.get("connection", {})
    hosts = connection.get("hosts")
    if hosts:
        return hosts
    return ["http://localhost:9200"]


def _resolve_credentials(config: dict[str, Any]) -> tuple[str | None, str | None]:
    connection = config.get("connection", {})
    username = os.environ.get("ELASTIC_USERNAME") or connection.get("username")
    password = os.environ.get("ELASTIC_PASSWORD") or connection.get("password")
    if username in (None, "", "null") or password in (None, "", "null"):
        return None, None
    return str(username), str(password)


def build_elasticsearch_client(config: dict[str, Any] | None = None) -> Elasticsearch:
    """Create a reusable Elasticsearch client from YAML config and .env overrides."""
    if config is None:
        config_path = os.environ.get("ELASTICSEARCH_CONFIG")
        config = load_yaml_config(config_path or DEFAULT_ELASTICSEARCH_CONFIG)

    connection = config.get("connection", {})
    hosts = _resolve_host(config)
    username, password = _resolve_credentials(config)

    client_kwargs: dict[str, Any] = {
        "hosts": hosts,
        "request_timeout": int(connection.get("request_timeout", 120)),
        "retry_on_timeout": True,
        "max_retries": int(connection.get("max_retries", 3)),
        "verify_certs": bool(connection.get("verify_certs", False)),
    }
    if username and password:
        client_kwargs["basic_auth"] = (username, password)

    client = Elasticsearch(**client_kwargs)
    _es_logger.debug("Elasticsearch client created for hosts={}", hosts)
    return client


def test_connection(
    client: Elasticsearch | None = None,
    config: dict[str, Any] | None = None,
    *,
    max_attempts: int = 3,
    retry_backoff_seconds: float = 2.0,
) -> dict[str, Any]:
    """
    Ping the cluster with retries and return connection status details.

    Returns
    -------
    dict with keys: connected, hosts, cluster_name, attempts, error (if failed)
    """
    if config is None:
        config_path = os.environ.get("ELASTICSEARCH_CONFIG")
        config = load_yaml_config(config_path or DEFAULT_ELASTICSEARCH_CONFIG)

    if client is None:
        client = build_elasticsearch_client(config)

    hosts = _resolve_host(config)
    connection = config.get("connection", {})
    max_attempts = int(connection.get("max_retries", max_attempts))
    retry_backoff_seconds = float(connection.get("retry_backoff_seconds", retry_backoff_seconds))

    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            if not client.ping():
                last_error = "Ping returned False"
                _es_logger.warning(
                    "Elasticsearch ping failed | attempt={}/{} | hosts={}",
                    attempt,
                    max_attempts,
                    hosts,
                )
            else:
                info = client.info()
                cluster_name = info.get("cluster_name", "unknown")
                version = info.get("version", {}).get("number", "unknown")
                _es_logger.info(
                    "Elasticsearch connected | hosts={} | cluster={} | version={} | attempt={}",
                    hosts,
                    cluster_name,
                    version,
                    attempt,
                )
                return {
                    "connected": True,
                    "hosts": hosts,
                    "cluster_name": cluster_name,
                    "version": version,
                    "attempts": attempt,
                    "error": None,
                }
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            _es_logger.warning(
                "Elasticsearch connection error | attempt={}/{} | hosts={} | error={}",
                attempt,
                max_attempts,
                hosts,
                exc,
            )

        if attempt < max_attempts:
            sleep_seconds = retry_backoff_seconds * attempt
            _es_logger.info("Retrying in {:.1f}s...", sleep_seconds)
            time.sleep(sleep_seconds)

    _es_logger.error(
        "Elasticsearch connection failed after {} attempts | hosts={} | error={}",
        max_attempts,
        hosts,
        last_error,
    )
    return {
        "connected": False,
        "hosts": hosts,
        "cluster_name": None,
        "version": None,
        "attempts": max_attempts,
        "error": last_error,
    }


def ping_cluster(client: Elasticsearch) -> bool:
    """Return True when the cluster responds to ping."""
    return test_connection(client=client, max_attempts=1)["connected"]
