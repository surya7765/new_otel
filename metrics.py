from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider, ObservableGauge
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from fastapi import Request
import psutil
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

serviceName = "mlass"
serviceVersion = "1.0.0"
serviceInstanceId = "instance-1"

# Initialize resource
resource = Resource(attributes={"service.name": serviceName,
                    "service.version": serviceVersion, "service.instance.id": serviceInstanceId})

# Initialize tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Initialize metrics
metric_exporter = OTLPMetricExporter(
    endpoint="http://otel-collector:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
metrics_provider = SDKMeterProvider(
    resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(metrics_provider)
meter = metrics.get_meter(__name__)

# Performance metrics
api_calls_counter = meter.create_counter(
    "api_calls", description="Count of API calls")
api_latency_histogram = meter.create_histogram(
    "api_latency", description="Latency of API calls")
api_errors_counter = meter.create_counter(
    "api_errors", description="Count of API errors")

# Observable gauges for CPU and Memory utilization


def cpu_usage_observable(options: metrics.CallbackOptions):
    return [metrics.Observation(value=psutil.cpu_percent(interval=None))]


def memory_usage_observable(options: metrics.CallbackOptions):
    return [metrics.Observation(value=psutil.virtual_memory().percent)]


meter.create_observable_gauge("cpu_usage", callbacks=[
                              cpu_usage_observable], description="CPU Usage", unit="percent")
meter.create_observable_gauge("memory_usage", callbacks=[
                              memory_usage_observable], description="Memory Usage", unit="percent")

# Middleware to record metrics and traces


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        api_calls_counter.add(1)

        try:
            response = await call_next(request)
            latency = time.time() - start_time
            api_latency_histogram.record(latency)
            logger.info(
                f"API latency for {request.url.path}: {latency:.4f} seconds")
            return response
        except Exception as e:
            api_errors_counter.add(1)
            logger.error(f"API error for {request.url.path}: {str(e)}")
            raise e


def instrument_app(app):
    FastAPIInstrumentor.instrument_app(app)
    app.add_middleware(MetricsMiddleware)
