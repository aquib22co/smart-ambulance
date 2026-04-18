from fastapi import FastAPI
from app.api.routes import webhook

app = FastAPI(title="Smart Ambulance System API")

app.include_router(webhook.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Ambulance System API"}
