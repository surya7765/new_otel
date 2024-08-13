from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider, ObservableGauge
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from fastapi import FastAPI, Request
import psutil
import time
import logging
import json

# Global variables for service information
serviceName = "mlass"
serviceVersion = "1.0.0"
serviceInstanceID = "instance-1"

# Custom log formatter
class CustomLogFormatter(logging.Formatter):
    def __init__(self, instance_id_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_id_func = instance_id_func

    def format(self, record):
        instance_id = self.instance_id_func()  # Dynamically get the current instanceId
        custom_log = {
            "instanceId": instance_id,
            "loglevel": record.levelname.lower(),
            "logs": record.getMessage()
        }
        return json.dumps(custom_log)

# Initialize the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to get the current instanceId
def get_current_instance_id():
    global serviceInstanceID
    return serviceInstanceID

# Check if there are no handlers attached to the logger
if not logger.handlers:
    # Default handler for standard output with basic formatting
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Apply custom log formatter
handler = logger.handlers[0]
handler.setFormatter(CustomLogFormatter(get_current_instance_id))


# Tracer initialization
tracer = trace.get_tracer(__name__)

# Global variables for metrics
API_CALLS = None
API_LATENCY = None
API_ERRORS = None
REQUEST_COUNT = None
ENDPOINT_POPULARITY = None
REQUEST_TIME = None
PEAK_USAGE_TIME = None
REQUEST_LATENCY = None
MODEL_VERSION = None
PREDICTION_ACCURACY = None

def create_resource(instance_id: str, service_id: str, app_id: str) -> Resource:
    return Resource(attributes={
        "service.name": serviceName,
        "service.version": serviceVersion,
        "service.instance.id": instance_id,
        "service.id": service_id,
        "app.id": app_id
    })

# Ensure TracerProvider is set up
def initialize_tracing(resource: Resource):
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)


def initialize_metrics(resource: Resource):
    global API_CALLS, API_LATENCY, API_ERRORS, REQUEST_COUNT, ENDPOINT_POPULARITY, REQUEST_TIME, PEAK_USAGE_TIME, REQUEST_LATENCY, MODEL_VERSION, PREDICTION_ACCURACY
    
    metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    metrics_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metrics_provider)
    meter = metrics.get_meter(__name__)

    # Initialize metrics
    API_CALLS = meter.create_counter("api_calls", description="Count of API calls")
    API_LATENCY = meter.create_histogram("api_latency", description="Latency of API calls")
    API_ERRORS = meter.create_counter("api_errors", description="Count of API errors")
    REQUEST_COUNT = meter.create_counter("request_count", description="Count of requests to each endpoint")
    ENDPOINT_POPULARITY = meter.create_counter("endpoint_popularity", description="Popularity of each endpoint based on request count")
    REQUEST_TIME = meter.create_histogram("request_time", description="Time taken to process each request")
    PEAK_USAGE_TIME = meter.create_observable_gauge("peak_usage_time", description="Peak usage time of the API")
    REQUEST_LATENCY = meter.create_histogram("request_latency", description="Latency of requests")
    MODEL_VERSION = meter.create_observable_gauge("model_version", description="Version of the model used")
    PREDICTION_ACCURACY = meter.create_observable_gauge("prediction_accuracy", description="Accuracy of predictions made by the model")

    def cpu_usage_observable(options: metrics.CallbackOptions):
        return [metrics.Observation(value=psutil.cpu_percent(interval=None))]

    def memory_usage_observable(options: metrics.CallbackOptions):
        return [metrics.Observation(value=psutil.virtual_memory().percent)]

    meter.create_observable_gauge("cpu_usage", callbacks=[cpu_usage_observable], description="CPU Usage", unit="percent")
    meter.create_observable_gauge("memory_usage", callbacks=[memory_usage_observable], description="Memory Usage", unit="percent")

# Initialize OpenTelemetry logging
def initialize_logging(resource: Resource):
    log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
    log_provider = LoggerProvider(resource=resource)
    log_processor = BatchLogRecordProcessor(log_exporter)
    log_provider.add_log_record_processor(log_processor)
    
    # Attach a handler that sends logs to OpenTelemetry
    otlp_logging_handler = logging.StreamHandler()
    otlp_logging_handler.setLevel(logging.INFO)
    otlp_logging_handler.setFormatter(CustomLogFormatter(get_current_instance_id))
    logger.addHandler(otlp_logging_handler)
    logger.setLevel(logging.INFO)


def verify_instance_api(instance_id: str, service_api_key: str):
    return {"instance_id": instance_id, "service_id": "service-123", "app_id": "app-456"}

def instrument_app(app: FastAPI):
    FastAPIInstrumentor.instrument_app(app)
    
    @app.middleware("http")
    async def metrics_and_traces_middleware(request: Request, call_next):
        try:
            # Ensure the instance ID is updated correctly
            global serviceInstanceID
            serviceInstanceID = request.query_params.get("instance_id", serviceInstanceID) or serviceInstanceID
            service_api_key = request.headers.get("Authorization", "Bearer default-api-key").split(" ")[-1]
            
            # Verification info should not be None; use default values
            verification_info = verify_instance_api(serviceInstanceID, service_api_key) or {}
            resource = create_resource(
                instance_id=verification_info.get("instance_id", serviceInstanceID),
                service_id=verification_info.get("service_id", "unknown_service"),
                app_id=verification_info.get("app_id", "unknown_app")
            )
            initialize_tracing(resource)
            initialize_metrics(resource)
            initialize_logging(resource)

            start_time = time.time()

            with trace.get_tracer(__name__).start_as_current_span(request.url.path) as span:
                span.set_attribute("instanceId", verification_info.get("instance_id", serviceInstanceID))
                span.set_attribute("logLevel", logging.getLevelName(logger.level))
                span.set_attribute("logs", logger.handlers[0].name if logger.handlers else "default")

                response = await call_next(request)

                latency = time.time() - start_time
                
                # Record API_CALLS, avoiding None values
                API_CALLS.add(1, attributes={
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })

                API_LATENCY.record(latency, attributes={
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].name if logger.handlers else "default"
                })

                REQUEST_TIME.record(latency, attributes={
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "endpoint": request.url.path
                })

                REQUEST_COUNT.add(1, attributes={
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "endpoint": request.url.path
                })

                ENDPOINT_POPULARITY.add(1, attributes={
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "endpoint": request.url.path
                })

                # Improved logging format
                logger.info({
                    "message": f"API latency for {request.url.path}: {latency:.4f} seconds",
                    "instanceId": verification_info.get("instance_id", serviceInstanceID),
                    "logLevel": logging.getLevelName(logger.level),
                    "logs": logger.handlers[0].formatter.format if logger.handlers else "default"
                })

                return response

        except Exception as e:
            # Log error if None value or another error occurs
            API_ERRORS.add(1, attributes={
                "instanceId": verification_info.get("instance_id", serviceInstanceID) if 'verification_info' in locals() else serviceInstanceID,
                "logLevel": logging.getLevelName(logger.level),
                "logs": logger.handlers[0].formatter.format if logger.handlers else "default"
            })
            logger.error({
                "message": f"Error processing request: {str(e)}",
                "instanceId": verification_info.get("instance_id", serviceInstanceID) if 'verification_info' in locals() else serviceInstanceID,
                "logLevel": logging.getLevelName(logger.level),
                "logs": logger.handlers[0].formatter.format if logger.handlers else "default"
            })
            raise e
