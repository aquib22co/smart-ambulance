# Smart Ambulance System

A FastAPI and Machine Learning-based project scaffold for a Smart Ambulance System.

## Project Setup

Follow these instructions to set up the environment and run the project locally.

### 1. Create a Virtual Environment

First, create a virtual environment to isolate your project dependencies.

**For Windows:**
```bash
python -m venv venv
```

**For macOS and Linux:**
```bash
python3 -m venv venv
```

### 2. Activate the Virtual Environment

Activate the virtual environment you just created.

**For Windows:**
```bash
.\venv\Scripts\activate
```

**For macOS and Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Run the Server

Start the FastAPI development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```

The server should now be running at `http://127.0.0.1:8000`. You can access the auto-generated API documentation (Swagger UI) by navigating to `http://127.0.0.1:8000/docs`.
