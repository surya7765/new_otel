import pandas as pd
from typing import List
from fastapi import FastAPI, HTTPException, Query, Header
from model import load_data, preprocess_data, create_model, train_model, predict
from metrics import instrument_app, logger

app = FastAPI()
instrument_app(app)

trained_model = None

@app.post("/train")
async def train(instance_id: str = Query(...), api_key: str = Header(...)):
    global trained_model
    try:
        data = load_data("data/stock_prices.csv")
        x_train, y_train = preprocess_data(data)
        model = create_model((x_train.shape[1], 1))
        trained_model = train_model(model, x_train, y_train)
        
        # Log the success message
        logger.info("Model trained successfully", extra={"instanceId": instance_id})
    except Exception as e:
        logger.error(f"Error during training: {e}", extra={"instanceId": instance_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict")
async def make_prediction(
    data: List[float],
    instance_id: str = Query(...),
    api_key: str = Header(...)):
    try:
        if trained_model is None:
            error_message = "Model not trained yet. Please train the model first."
            logger.error(error_message, extra={"instanceId": instance_id})
            raise HTTPException(status_code=400, detail=error_message)
        
        new_data = pd.DataFrame(data, columns=["Close"])
        x_new, _, _ = preprocess_data(new_data)
        predictions = predict(trained_model, x_new)
        
        # Log the predictions
        logger.info(f"Predictions made successfully: {predictions.tolist()}", extra={"instanceId": instance_id})
    except Exception as e:
        logger.error(f"Error during prediction: {e}", extra={"instanceId": instance_id})
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
