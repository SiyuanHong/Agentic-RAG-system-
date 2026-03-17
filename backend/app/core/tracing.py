import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_tracing() -> None:
    if not settings.PHOENIX_ENABLED:
        logger.info("Phoenix tracing disabled")
        return

    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        tracer_provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT)
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(f"Phoenix tracing initialized → {settings.PHOENIX_COLLECTOR_ENDPOINT}")
    except Exception as e:
        logger.warning(f"Failed to initialize Phoenix tracing: {e}")
