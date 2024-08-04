import pandas as pd
from typing import List
from fastapi import FastAPI, HTTPException
from model import load_data, preprocess_data, create_model, train_model, predict
from metrics import instrument_app

# Initialize FastAPI
app = FastAPI()

# Instrument the FastAPI app for OpenTelemetry
instrument_app(app)

# Global variable to store the trained model
trained_model = None

@app.post("/train")
async def train():
    global trained_model
    try:
        data = load_data("data/stock_prices.csv")
        x_train, y_train = preprocess_data(data)
        model = create_model((x_train.shape[1], 1))
        trained_model = train_model(model, x_train, y_train)  # Save the trained model
        return {"message": "Model trained successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
async def make_prediction():
    global trained_model
    try:
        if trained_model is None:
            raise HTTPException(status_code=400, detail="Model not trained yet. Please train the model first.")
        
        data = load_data("data/stock_prices.csv")
        x_train, _ = preprocess_data(data)
        predictions = predict(trained_model, x_train)
        return {"predictions": predictions.tolist()}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
@app.post("/predict")
async def make_prediction(data: List[float]):    
    try:

        if trained_model is None:
            raise HTTPException(status_code=400, detail="Model not trained yet. Please train the model first.")
        
        # Assume `data` is a list of the latest 'Close' prices
        new_data = pd.DataFrame(data, columns=["Close"])

        # Preprocess the new data
        x_new, _, _ = preprocess_data(new_data)
        
        # Make predictions
        predictions = predict(train_model, x_new)
        
        response = {"predictions": predictions.tolist()}
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
[
    {"Date": "2023-07-01", "Close": 152.48},
    {"Date": "2023-07-02", "Close": 301.79},
    {"Date": "2023-07-03", "Close": 455.03},
    {"Date": "2023-07-04", "Close": 612.65},
    {"Date": "2023-07-05", "Close": 761.48},
    {"Date": "2023-07-06", "Close": 920.13},
    {"Date": "2023-07-07", "Close": 1068.29},
    {"Date": "2023-07-08", "Close": 1222.55},
    {"Date": "2023-07-09", "Close": 1361.38},
    {"Date": "2023-07-10", "Close": 1514.13},
    {"Date": "2023-07-11", "Close": 1667.43},
    {"Date": "2023-07-12", "Close": 1823.83},
    {"Date": "2023-07-13", "Close": 1967.88},
    {"Date": "2023-07-14", "Close": 2113.64},
    {"Date": "2023-07-15", "Close": 2264.04},
    {"Date": "2023-07-16", "Close": 2413.61},
    {"Date": "2023-07-17", "Close": 2567.03},
    {"Date": "2023-07-18", "Close": 2717.02},
    {"Date": "2023-07-19", "Close": 2870.91},
    {"Date": "2023-07-20", "Close": 3018.71},
    {"Date": "2023-07-21", "Close": 3173.62},
    {"Date": "2023-07-22", "Close": 3321.83},
    {"Date": "2023-07-23", "Close": 3478.12},
    {"Date": "2023-07-24", "Close": 3633.10},
    {"Date": "2023-07-25", "Close": 3788.33},
    {"Date": "2023-07-26", "Close": 3943.49},
    {"Date": "2023-07-27", "Close": 4095.45},
    {"Date": "2023-07-28", "Close": 4249.42},
    {"Date": "2023-07-29", "Close": 4407.63},
    {"Date": "2023-07-30", "Close": 4557.82},
    {"Date": "2023-07-31", "Close": 4713.18},
    {"Date": "2023-08-01", "Close": 4865.00},
    {"Date": "2023-08-02", "Close": 5017.27},
    {"Date": "2023-08-03", "Close": 5167.11},
    {"Date": "2023-08-04", "Close": 5321.97},
    {"Date": "2023-08-05", "Close": 5474.20},
    {"Date": "2023-08-06", "Close": 5625.84},
    {"Date": "2023-08-07", "Close": 5779.36},
    {"Date": "2023-08-08", "Close": 5932.09},
    {"Date": "2023-08-09", "Close": 6081.74},
    {"Date": "2023-08-10", "Close": 6233.96},
    {"Date": "2023-08-11", "Close": 6385.79},
    {"Date": "2023-08-12", "Close": 6536.16},
    {"Date": "2023-08-13", "Close": 6688.48},
    {"Date": "2023-08-14", "Close": 6840.56},
    {"Date": "2023-08-15", "Close": 6992.89},
    {"Date": "2023-08-16", "Close": 7144.36},
    {"Date": "2023-08-17", "Close": 7297.54},
    {"Date": "2023-08-18", "Close": 7447.46},
    {"Date": "2023-08-19", "Close": 7601.54},
    {"Date": "2023-08-20", "Close": 7755.37},
    {"Date": "2023-08-21", "Close": 7906.98},
    {"Date": "2023-08-22", "Close": 8058.75},
    {"Date": "2023-08-23", "Close": 8213.52},
    {"Date": "2023-08-24", "Close": 8365.74},
    {"Date": "2023-08-25", "Close": 8517.89},
    {"Date": "2023-08-26", "Close": 8671.65},
    {"Date": "2023-08-27", "Close": 8826.34},
    {"Date": "2023-08-28", "Close": 8981.19}
]
"""
