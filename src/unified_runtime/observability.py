from __future__ import annotations

import os
from typing import Any

# Optional OpenTelemetry setup
try:  # pragma: no cover
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
except Exception:  # pragma: no cover
    trace = None  # type: ignore

_tracer = None


def setup_tracing_if_enabled() -> None:
    global _tracer
    if _tracer is not None or trace is None:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name = os.getenv("OTEL_SERVICE_NAME", "liquid-hive-upgrade")
    if not endpoint:
        return
    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
    except Exception:
        _tracer = None


def get_tracer() -> Any:
    if _tracer is None:
        setup_tracing_if_enabled()
    return _tracer