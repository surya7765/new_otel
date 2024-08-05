import pandas as pd
from typing import List
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from model import load_data, preprocess_data, create_model, train_model, predict
from metrics import instrument_app

# Define a model for the request body
class InstanceInfo(BaseModel):
    instance_id: str
    service_api_key: str

# Initialize FastAPI
app = FastAPI()

# Instrument the FastAPI app for OpenTelemetry
instrument_app(app)

# Global variable to store the trained model
trained_model = None

@app.post("/train")
async def train(
    instance_info: InstanceInfo = Body(...)):
    global trained_model
    try:
        data = load_data("data/stock_prices.csv")
        x_train, y_train = preprocess_data(data)
        model = create_model((x_train.shape[1], 1))
        trained_model = train_model(model, x_train, y_train)  # Save the trained model
        return {"message": "Model trained successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict")
async def make_prediction(
    data: List[float],
    instance_info: InstanceInfo = Body(...)):
    try:
        if trained_model is None:
            raise HTTPException(status_code=400, detail="Model not trained yet. Please train the model first.")
        
        # Assume `data` is a list of the latest 'Close' prices
        new_data = pd.DataFrame(data, columns=["Close"])

        # Preprocess the new data
        x_new, _, _ = preprocess_data(new_data)
        
        # Make predictions
        predictions = predict(trained_model, x_new)
        
        response = {"predictions": predictions.tolist()}
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
