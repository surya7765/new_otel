import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.metrics import MeterProvider, Counter, Histogram
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider
import logging
import time
import psutil  # For resource utilization metrics

# Configure OpenTelemetry Tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Configure OpenTelemetry Metrics
metrics_provider = SDKMeterProvider()
meter = metrics_provider.get_meter(__name__)
performance_counter = meter.create_counter("api_calls", description="Count of API calls")
latency_histogram = meter.create_histogram("api_latency", description="Latency of API calls")
error_counter = meter.create_counter("api_errors", description="Count of API errors")
resource_counter = meter.create_counter("resource_usage", description="Resource usage metrics")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track API Calls
def record_api_call():
    performance_counter.add(1)
    
# Track API Latency
def track_latency(start_time):
    end_time = time.time()
    latency = end_time - start_time
    latency_histogram.record(latency)
    logger.info(f"API latency: {latency:.4f} seconds")

# Track Errors
def record_error():
    error_counter.add(1)

# Track Resource Utilization
def log_resource_utilization():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    resource_counter.add(cpu_usage)
    resource_counter.add(memory_usage)
    logger.info(f"CPU usage: {cpu_usage}%")
    logger.info(f"Memory usage: {memory_usage}%")

def load_data(file_path):
    with tracer.start_as_current_span("load_data"):
        start_time = time.time()
        try:
            data = pd.read_csv(file_path)
            record_api_call()
            log_resource_utilization()
            return data[:5000]
        except Exception as e:
            record_error()
            logger.error(f"Error loading data: {e}")
        finally:
            track_latency(start_time)

def preprocess_data(data):
    with tracer.start_as_current_span("preprocess_data"):
        start_time = time.time()
        try:
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))
            
            # Create sequences
            sequence_length = 60
            x, y = [], []
            for i in range(sequence_length, len(scaled_data)):
                x.append(scaled_data[i-sequence_length:i, 0])
                y.append(scaled_data[i, 0])
            
            x, y = np.array(x), np.array(y)
            x = np.reshape(x, (x.shape[0], x.shape[1], 1))
            record_api_call()
            log_resource_utilization()
            return x, y, scaler
        except Exception as e:
            record_error()
            logger.error(f"Error preprocessing data: {e}")
        finally:
            track_latency(start_time)

def create_model(input_shape):
    with tracer.start_as_current_span("create_model"):
        start_time = time.time()
        try:
            model = Sequential()
            model.add(LSTM(50, return_sequences=True, input_shape=input_shape))
            model.add(LSTM(50, return_sequences=False))
            model.add(Dropout(0.2))
            model.add(Dense(1))
            
            model.compile(optimizer='adam', loss='mean_squared_error')
            record_api_call()
            log_resource_utilization()
            return model
        except Exception as e:
            record_error()
            logger.error(f"Error creating model: {e}")
        finally:
            track_latency(start_time)

def train_model(model, x_train, y_train):
    with tracer.start_as_current_span("train_model"):
        start_time = time.time()
        try:
            model.fit(x_train, y_train, epochs=10, batch_size=32, verbose=1)
            record_api_call()
            log_resource_utilization()
            return model
        except Exception as e:
            record_error()
            logger.error(f"Error training model: {e}")
        finally:
            track_latency(start_time)

def predict(model, x_test):
    with tracer.start_as_current_span("predict"):
        start_time = time.time()
        try:
            predictions = model.predict(x_test)
            record_api_call()
            log_resource_utilization()
            return predictions
        except Exception as e:
            record_error()
            logger.error(f"Error predicting: {e}")
        finally:
            track_latency(start_time)

# Example usage
if __name__ == "__main__":
    data = load_data("data/stock_prices.csv")
    x, y, scaler = preprocess_data(data)
    model = create_model((x.shape[1], 1))
    trained_model = train_model(model, x, y)
    predictions = predict(trained_model, x)
    logger.info("Prediction complete")
