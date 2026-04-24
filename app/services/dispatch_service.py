import logging
import random
import math
import pickle
import os
import pandas as pd
from datetime import datetime
from app.services.memory_service import update_dispatch_status
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)

# Paths to model artifacts
MODEL_DIR = os.path.join(os.getcwd(), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
LE_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

# Simulated Mumbai Zones
MUMBAI_ZONES = {
    "South Mumbai":    {"lat": (19.05, 19.09), "lon": (72.82, 72.88)},
    "Central Mumbai":  {"lat": (19.09, 19.14), "lon": (72.83, 72.92)},
    "North Mumbai":    {"lat": (19.14, 19.22), "lon": (72.83, 72.94)},
    "Eastern Suburbs": {"lat": (19.07, 19.18), "lon": (72.88, 72.94)},
    "Western Suburbs": {"lat": (19.10, 19.21), "lon": (72.82, 72.87)},
}

# Global variables for model and label encoder
model = None
label_encoder = None

def load_model():
    global model, label_encoder
    try:
        if os.path.exists(MODEL_PATH) and os.path.exists(LE_PATH):
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            with open(LE_PATH, "rb") as f:
                label_encoder = pickle.load(f)
            logger.info("ML Model and Label Encoder loaded successfully.")
        else:
            logger.warning(f"Model artifacts not found at {MODEL_DIR}. Using fallback logic.")
    except Exception as e:
        logger.error(f"Error loading ML model: {e}")

# Initial load
load_model()

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def generate_simulated_fleet(n=10):
    zones = list(MUMBAI_ZONES.keys())
    fleet = []
    for i in range(n):
        zone_name = random.choice(zones)
        z = MUMBAI_ZONES[zone_name]
        fleet.append({
            "ambulance_id": f"AMB-{i+101:03d}",
            "lat": random.uniform(*z["lat"]),
            "lon": random.uniform(*z["lon"]),
            "is_available": 1, # Use 1/0 for ML model
            "zone": zone_name,
            "fuel_level": round(random.uniform(0.4, 1.0), 2),
            "crew_experience": random.randint(1, 10)
        })
    return fleet

def predict_eta_ml(accident_lat, accident_lon, ambulance, severity, weather, hour):
    """
    Predicts ETA using the trained GradientBoostingRegressor model.
    """
    global model, label_encoder
    
    dist = haversine_km(accident_lat, accident_lon, ambulance["lat"], ambulance["lon"])
    
    if model is None or label_encoder is None:
        # Fallback to physics logic if model is missing
        return round(dist * 2.5 + 5, 2) 

    try:
        # Prepare feature dictionary matching FEATURE_COLS in train.py
        now = datetime.now()
        day_of_week = now.isoweekday() # 1-7 (Mon-Sun)
        
        # Mapping for zones
        zone_enc = label_encoder.transform([ambulance["zone"]])[0]
        
        features = {
            "distance_km": dist,
            "severity": int(severity),
            "weather": int(weather),
            "light_conditions": 1, # Default: Daylight
            "road_surface": 1,     # Default: Dry
            "speed_limit": 50.0,   # Default
            "num_casualties": 1,    # Default
            "day_of_week": day_of_week,
            "road_type": 1,
            "urban_rural": 1,
            "hour_of_day": float(hour),
            "is_rush_hour": int(8 <= hour <= 10 or 17 <= hour <= 20),
            "is_night": int(hour >= 22 or hour <= 5),
            "is_weekend": int(day_of_week in [6, 7]),
            "is_available": int(ambulance["is_available"]),
            "fuel_level": float(ambulance["fuel_level"]),
            "crew_experience": int(ambulance["crew_experience"]),
            "amb_zone_enc": zone_enc
        }
        
        # Convert to DataFrame with correct column order
        feature_cols = [
            "distance_km", "severity", "weather", "light_conditions", "road_surface",
            "speed_limit", "num_casualties", "day_of_week", "road_type", "urban_rural",
            "hour_of_day", "is_rush_hour", "is_night", "is_weekend", "is_available",
            "fuel_level", "crew_experience", "amb_zone_enc"
        ]
        
        X = pd.DataFrame([features])[feature_cols]
        eta = model.predict(X)[0]
        
        return round(max(eta, 2.0), 2)
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return round(dist * 2.5 + 5, 2)

async def allocate_ambulance(phone_number: str, accident_data: dict):
    try:
        acc_lat = float(accident_data.get("latitude", 0))
        acc_lon = float(accident_data.get("longitude", 0))
        severity = int(accident_data.get("severity", 3))
        weather = int(accident_data.get("weather", 1))
        hour = accident_data.get("timestamp_of_accident", datetime.now().hour)

        # 1. Get candidates
        fleet = generate_simulated_fleet(20)
        available = [a for a in fleet if a["is_available"]]
        
        if not available:
            logger.warning("No available ambulances found.")
            return False

        # 2. Predict ETA for all candidates using ML model
        candidates = []
        for amb in available:
            eta = predict_eta_ml(acc_lat, acc_lon, amb, severity, weather, hour)
            candidates.append({**amb, "predicted_eta": eta})
        
        candidates.sort(key=lambda x: x["predicted_eta"])
        
        selected_amb = None
        
        # 3. Apply Severity Rules
        if severity == 1:
            selected_amb = candidates[0]
        elif severity == 2:
            selected_amb = candidates[0]
        else:
            if len(candidates) > 1:
                nearest = candidates[0]
                second = candidates[1]
                if (second["predicted_eta"] - nearest["predicted_eta"]) < 5.0:
                    selected_amb = second
                else:
                    selected_amb = nearest
            else:
                selected_amb = candidates[0]

        # 4. Finalize Dispatch
        if selected_amb:
            await update_dispatch_status(phone_number, selected_amb["ambulance_id"], selected_amb["predicted_eta"])
            msg = (
                f"🚑 *AMBULANCE DISPATCHED*\n\n"
                f"Ambulance *{selected_amb['ambulance_id']}* is on the way.\n"
                f"⏱️ ML-Predicted Arrival: *{selected_amb['predicted_eta']} minutes*.\n\n"
                f"Please stay calm. help is arriving."
            )
            await send_whatsapp_message(phone_number, msg)
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error in ambulance allocation: {e}")
        return False
