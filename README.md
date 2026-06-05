# 🚑 Rapid Care: Smart Ambulance System

**Rapid Care** is a modern, automated emergency response system designed to streamline ambulance dispatch and live tracking. Leveraging Large Language Models (LLMs) for conversational triage, Machine Learning (ML) for travel time prediction, and interactive web mapping, the platform minimizes response latency during critical medical emergencies.

---

## 🏗️ System Architecture

The Smart Ambulance System is structured as a highly responsive event-driven architecture, coordinating user interaction, real-time database updates, ML inference, and visual tracking.

### 🔄 End-to-End Workflow
![alt text](/Screenshots/Screenshot%202026-06-05%20171317.png)

---

## 🛠️ Technology Stack

The platform is constructed using modern, robust libraries and APIs to ensure speed, scalability, and developer ergonomics:

| Component | Technology | Role & Purpose |
| :--- | :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance ASGI web framework for building APIs, utilizing python-typed schemas. |
| **Triage LLM** | [Groq / OpenAI SDK](https://github.com/openai/openai-python) | Powers the conversational triage chatbot utilizing the `openai/gpt-oss-120b` (or Groq standard) models. |
| **Database** | [MongoDB Atlas](https://www.mongodb.com/atlas) | NoSQL database for managing conversational sessions, fleet states, and accident reports. |
| **DB Driver** | [Motor](https://motor.readthedocs.io/) | Asynchronous Python driver for MongoDB, preventing blocking I/O calls inside FastAPI. |
| **Machine Learning** | [Scikit-Learn](https://scikit-learn.org/) | Model training and inference utilizing a `GradientBoostingRegressor` to predict arrival times. |
| **Data Processing**| [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) | Feature engineering, raw Excel dataset handling, and spatial calculations. |
| **Live Map** | [Leaflet.js](https://leafletjs.com/) | Client-side interactive maps rendered dynamically using CartoDB dark-themed tiles. |
| **Messaging** | [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) | Instant user notification channel, handling text messages and live location shares. |
| **Tunneling** | [Ngrok](https://ngrok.com/) | Secure public URL tunneling to expose the local FastAPI port (8000) to Meta's webhook servers. |

---

## 🤖 Machine Learning & Algorithmic Dispatch

### 1. Travel Time (ETA) Prediction Model
Instead of relying on simple Euclidean distances, the dispatch engine uses a **Gradient Boosting Regressor** model trained on historical Mumbai accident records. The model takes into account:
- **Spatial Features**: Haversine distance between the ambulance zone and the accident coordinates.
- **Temporal Features**: Time of day (0.00-23.99), weekday vs. weekend, and whether it falls during Mumbai rush hours (08:00-10:00, 17:00-20:00).
- **Environmental Conditions**: Weather severity index (Fine, Rain, Snow, Flooding, Fog) and light conditions.
- **Road Dynamics**: Speed limits, road surface status (Dry, Wet, Flooding), and road type.
- **Operational Data**: Fuel levels, crew experience (years), and ambulance availability.

### 2. Triage Severity & Allocation Logic
When the triage assistant compiles the incident report, it assigns a severity classification:
*   **Severity 1 (Fatal)**: Unconscious, not breathing, or heavy bleeding.
*   **Severity 2 (Serious)**: Moderate bleeding or immobility.
*   **Severity 3 (Slight)**: Minor cuts, conscious, and mobile.

**Allocation Rules:**
- For **Severity 1 & 2** cases, the system allocates the absolute closest ambulance (lowest predicted ETA) immediately.
- For **Severity 3** cases, if the closest and second-closest ambulances are within a 5-minute ETA margin of each other, the system dispatches the second-closest ambulance. This keeps the closest unit free for nearby high-priority life-or-death emergencies.

---

## 🖼️ Application Preview & Interface

> [!NOTE]
> Below are placeholders to capture the production workflow and user interface. Replace these with actual images when running live.

### 📱 1. Conversational Triage (WhatsApp)
This view highlights the interactive, minimal-step triage questionnaire guiding the reporter during an emergency.

![alt text](/Screenshots/ss_1.jpeg)

![alt text](/Screenshots/ss_2.png)

![alt text](/Screenshots/ss_3.png)

---

### 🗺️ 2. Live Ambulance Tracking Dashboard
A browser-based tracking screen served dynamically for each dispatch. It renders an interactive dark map detailing the route and simulated movements.

![alt text](/Screenshots/tracking.png)

---

### 📖 3. API Documentation & Schema Explorer
FastAPI auto-generates interactive OpenAPI schemas, accessible during local testing.

![alt text](/Screenshots/API.png)

---

## ⚙️ Local Setup & Installation

### Prerequisite Checklist
- **Python 3.10+** installed.
- **MongoDB** instance running locally or via a MongoDB Atlas cloud URI.
- A **Meta Developer Account** with a WhatsApp business test phone number.
- **Ngrok** CLI installed.

### Step-by-Step Setup

#### 1. Clone & Set Up Virtual Environment
Initialize a virtual environment to isolate dependency installation:

**Windows (PowerShell):**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install Project Dependencies
Install the required packages listed in the requirements manifest:
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables
Create a `.env` file in the root directory and define the following configuration variables:
```env
WHATSAPP_ACCESS_TOKEN=your_whatsapp_temporary_or_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_whatsapp_business_account_id
VERIFY_TOKEN=your_custom_webhook_verify_token
AI_API_KEY=your_groq_or_openai_api_key
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/smartAmbulance
NGROK_URL=https://<your-subdomain>.ngrok-free.app
```

#### 4. Run the Dev Server
Launch the FastAPI server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server runs on `http://127.0.0.1:8000`. You can inspect the Swagger UI explorer at `http://127.0.0.1:8000/docs`.

#### 5. Expose Webhook via Ngrok
Expose your local development port (8000) to receive Meta webhook callbacks:
```bash
ngrok http 8000
```
1. Copy the forwarding HTTPS address (e.g., `https://xxxx.ngrok-free.app`).
2. Update the `NGROK_URL` key in your `.env` file with this forwarding URL.
3. Configure the WhatsApp Webhook URL in your Facebook Developer Console to:
   `https://xxxx.ngrok-free.app/webhook`
4. Input the configured `VERIFY_TOKEN` and subscribe to **messages** callbacks.
