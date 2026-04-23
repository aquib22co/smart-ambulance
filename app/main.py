from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import webhook
from app.db.database import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="Smart Ambulance System API", lifespan=lifespan)

app.include_router(webhook.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Ambulance System API"}
