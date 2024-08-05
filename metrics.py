from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider, ObservableGauge
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from fastapi import FastAPI, Request
import psutil
import time
import logging
import json

# Initialize logging
serviceName = "mlass"
serviceVersion = "1.0.0"
defaultServiceInstanceId = "instance-1"

# Custom formatter to include instanceId, loglevel, and logs
class CustomLogFormatter(logging.Formatter):
    def format(self, record):
        custom_log = {
            "instanceId": defaultServiceInstanceId,
            "loglevel": record.levelname.lower(),
            "logs": record.getMessage()
        }
        return json.dumps(custom_log)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the logger has handlers. If not, add one.
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Apply the custom formatter
handler = logger.handlers[0]
handler.setFormatter(CustomLogFormatter())

tracer = trace.get_tracer(__name__)

# Initialize resource
def create_resource(instance_id: str, service_id: str, app_id: str) -> Resource:
    return Resource(attributes={
        "service.name": serviceName,
        "service.version": serviceVersion,
        "service.instance.id": instance_id,
        "service.id": service_id,
        "app.id": app_id
    })

def initialize_tracing(resource: Resource):
    trace.set_tracer_provider(TracerProvider(resource=resource))
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://otel-collector:4317", insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

def initialize_metrics(resource: Resource):
    metric_exporter = OTLPMetricExporter(
        endpoint="http://otel-collector:4317", insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    metrics_provider = SDKMeterProvider(
        resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metrics_provider)
    meter = metrics.get_meter(__name__)

    # Performance metrics
    global api_calls_counter, api_latency_histogram, api_errors_counter
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

def verify_instance_api(instance_id: str, service_api_key: str):
    # Dummy implementation for verification
    return {
        "instance_id": instance_id,
        "service_id": "service-123",
        "app_id": "app-456"
    }

def instrument_app(app: FastAPI):
    FastAPIInstrumentor.instrument_app(app)
    
    @app.middleware("http")
    async def metrics_and_traces_middleware(request: Request, call_next):
        # Parse the JSON body to extract instance_id and service_api_key
        request_body = await request.json()
        instance_id = request_body.get("instance_id", defaultServiceInstanceId)
        service_api_key = request_body.get("service_api_key", "default-api-key")
        
        verification_info = verify_instance_api(instance_id, service_api_key)

        # Create resource with dynamic attributes
        resource = create_resource(
            instance_id=verification_info["instance_id"],
            service_id=verification_info["service_id"],
            app_id=verification_info["app_id"]
        )
        initialize_tracing(resource)
        initialize_metrics(resource)

        start_time = time.time()
        api_calls_counter.add(1, attributes={
            "instanceId": verification_info["instance_id"],
            "logLevel": logging.getLevelName(logger.level),
            "logs": logger.handlers[0].name if logger.handlers else "default"
        })

        with trace.get_tracer(__name__).start_as_current_span(request.url.path) as span:
            span.set_attribute("instanceId", verification_info["instance_id"])
            span.set_attribute("logLevel", logging.getLevelName(logger.level))
            span.set_attribute("logs", logger.handlers[0].name if logger.handlers else "default")

            try:
                response = await call_next(request)
                latency = time.time() - start_time
                api_latency_histogram.record(latency, attributes={
                    "instanceId": verification_info["instance_id"],
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })
                
                logger.info({
                    "message": f"API latency for {request.url.path}: {latency:.4f} seconds",
                    "instanceId": verification_info["instance_id"],
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })

                return response
            except Exception as e:
                api_errors_counter.add(1, attributes={
                    "instanceId": verification_info["instance_id"],
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })
                logger.error({
                    "message": f"API error for {request.url.path}: {str(e)}",
                    "instanceId": verification_info["instance_id"],
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise e
