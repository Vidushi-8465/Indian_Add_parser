"""Elasticsearch client factory."""

from __future__ import annotations

import os
from typing import Any

from elasticsearch import Elasticsearch
from loguru import logger

from utils.constants import DEFAULT_ELASTICSEARCH_CONFIG
from utils.file_utils import load_yaml_config


def build_elasticsearch_client(config: dict[str, Any] | None = None) -> Elasticsearch:
    """Create an Elasticsearch client from config and environment overrides."""
    if config is None:
        config_path = os.environ.get("ELASTICSEARCH_CONFIG")
        config = load_yaml_config(config_path or DEFAULT_ELASTICSEARCH_CONFIG)

    connection = config.get("connection", {})
    hosts = connection.get("hosts") or [os.environ.get("ELASTIC_HOST", "http://localhost:9200")]
    username = os.environ.get("ELASTIC_USERNAME") or connection.get("username")
    password = os.environ.get("ELASTIC_PASSWORD") or connection.get("password")

    client_kwargs: dict[str, Any] = {
        "hosts": hosts,
        "request_timeout": connection.get("request_timeout", 120),
        "retry_on_timeout": True,
        "max_retries": connection.get("max_retries", 3),
        "verify_certs": connection.get("verify_certs", False),
    }
    if username and password:
        client_kwargs["basic_auth"] = (username, password)

    client = Elasticsearch(**client_kwargs)
    logger.bind(module="es_index.client").info("Connected to Elasticsearch at {}", hosts)
    return client


def ping_cluster(client: Elasticsearch) -> bool:
    """Return True when the cluster responds to ping."""
    try:
        return bool(client.ping())
    except Exception:  # noqa: BLE001
        return False
