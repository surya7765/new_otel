import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from fastapi import HTTPException
import logging
from metrics import tracer

# Set up logging
logger = logging.getLogger(__name__)

# Load and preprocess data
def load_data(file_path):
    with tracer.start_as_current_span("load_data"):
        try:
            data = pd.read_csv(file_path)
            return data[:5000]
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise HTTPException(status_code=500, detail="Error loading data")

def preprocess_data(data):
    with tracer.start_as_current_span("preprocess_data"):
        try:
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))
            sequence_length = 60
            x, y = [], []
            for i in range(sequence_length, len(scaled_data)):
                x.append(scaled_data[i-sequence_length:i, 0])
                y.append(scaled_data[i, 0])
            x, y = np.array(x), np.array(y)
            x = np.reshape(x, (x.shape[0], x.shape[1], 1))
            return x, y
        except Exception as e:
            logger.error(f"Error preprocessing data: {e}")
            raise HTTPException(status_code=500, detail="Error preprocessing data")

# Create LSTM model
def create_model(input_shape):
    with tracer.start_as_current_span("create_model"):
        try:
            model = Sequential()
            model.add(LSTM(50, return_sequences=True, input_shape=input_shape))
            model.add(LSTM(50, return_sequences=False))
            model.add(Dropout(0.2))
            model.add(Dense(1))
            model.compile(optimizer='adam', loss='mean_squared_error')
            return model
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            raise HTTPException(status_code=500, detail="Error creating model")

# Train the model
def train_model(model, x_train, y_train):
    with tracer.start_as_current_span("train_model"):
        try:
            model.fit(x_train, y_train, epochs=10, batch_size=32, verbose=1)
            return model
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise HTTPException(status_code=500, detail="Error training model")

# Predict
def predict(model, x_test):
    with tracer.start_as_current_span("predict"):
        try:
            predictions = model.predict(x_test)
            
            # Ensure predictions are valid (no NaN or infinite values)
            if not np.isfinite(predictions).all():
                raise ValueError("Predictions contain NaN or infinite values.")
            
            return predictions
        except Exception as e:
            logger.error(f"Error predicting: {e}")
            raise HTTPException(status_code=500, detail="Error predicting")
