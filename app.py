import pandas as pd
from typing import List
from fastapi import FastAPI, HTTPException, Query, Header
from model import load_data, preprocess_data, create_model, train_model, predict
from metrics import instrument_app

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
        return {"message": "Model trained successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict")
async def make_prediction(
    data: List[float],
    instance_id: str = Query(...),
    api_key: str = Header(...)):
    try:
        if trained_model is None:
            raise HTTPException(status_code=400, detail="Model not trained yet. Please train the model first.")
        
        new_data = pd.DataFrame(data, columns=["Close"])
        x_new, _, _ = preprocess_data(new_data)
        predictions = predict(trained_model, x_new)
        return {"predictions": predictions.tolist()}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
