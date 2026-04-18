from fastapi import FastAPI

app = FastAPI(title="Smart Ambulance System API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Ambulance System API"}
