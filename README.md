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

### 4. Configure Environment Variables

Create a `.env` file in the root directory (`smart-ambulance-system`) and add the following keys with your own credentials:

```env
WHATSAPP_ACCESS_TOKEN=your_whatsapp_temporary_or_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_whatsapp_business_account_id
VERIFY_TOKEN=your_custom_webhook_verify_token
AI_API_KEY=your_groq_or_openai_api_key
MONGODB_URI=your_mongodb_connection_string
```

### 5. Run the Server

Start the FastAPI development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```

The server should now be running at `http://127.0.0.1:8000`. You can access the auto-generated API documentation (Swagger UI) by navigating to `http://127.0.0.1:8000/docs`.

### 6. Expose the Local Webhook using ngrok

To receive webhook events from the Meta/WhatsApp API on your local machine, you need to expose your local server to the internet using `ngrok`.

1. Download and install [ngrok](https://ngrok.com/download).
2. Authenticate ngrok using your authtoken (if you haven't already):
   ```bash
   ngrok config add-authtoken <your-authtoken>
   ```
3. Start an HTTP tunnel pointing to your local FastAPI port (8000):
   ```bash
   ngrok http 8000
   ```
4. Copy the **Forwarding URL** (e.g., `https://<random-id>.ngrok-free.app`) provided by ngrok.
5. In your Meta App Dashboard, set your Webhook URL to: 
   `https://<random-id>.ngrok-free.app/webhook`
   and provide your verification token.
