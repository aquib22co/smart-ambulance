import logging
import random
import math
from datetime import datetime
from app.services.memory_service import update_dispatch_status
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)

# Simulated Mumbai Zones from train.py
MUMBAI_ZONES = {
    "South Mumbai":    {"lat": (19.05, 19.09), "lon": (72.82, 72.88)},
    "Central Mumbai":  {"lat": (19.09, 19.14), "lon": (72.83, 72.92)},
    "North Mumbai":    {"lat": (19.14, 19.22), "lon": (72.83, 72.94)},
    "Eastern Suburbs": {"lat": (19.07, 19.18), "lon": (72.88, 72.94)},
    "Western Suburbs": {"lat": (19.10, 19.21), "lon": (72.82, 72.87)},
}

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def generate_simulated_fleet(n=10):
    """
    Generates a list of simulated ambulances.
    In a real app, this would come from a database or live tracking service.
    """
    zones = list(MUMBAI_ZONES.keys())
    fleet = []
    for i in range(n):
        zone_name = random.choice(zones)
        z = MUMBAI_ZONES[zone_name]
        fleet.append({
            "ambulance_id": f"AMB-{i+101:03d}",
            "lat": random.uniform(*z["lat"]),
            "lon": random.uniform(*z["lon"]),
            "is_available": random.random() > 0.1,  # 90% availability
            "zone": zone_name
        })
    return fleet

def predict_eta(accident_lat, accident_lon, ambulance, severity, weather, hour):
    """
    Predicts ETA in minutes. 
    Uses the physics-based logic from train.py as a reliable fallback/simulation.
    """
    dist = haversine_km(accident_lat, accident_lon, ambulance["lat"], ambulance["lon"])
    
    # Base logic from train.py
    base_speed = 40 
    amb_speed = base_speed * 1.20  # siren boost
    
    # Traffic multiplier
    if 8 <= hour <= 10 or 17 <= hour <= 20:
        traffic = 2.0
    elif 12 <= hour <= 14:
        traffic = 1.4
    elif hour >= 22 or hour <= 5:
        traffic = 0.9
    else:
        traffic = 1.2

    # Simple multipliers (simplified from train.py)
    weather_mult = {1: 1.0, 2: 1.25, 3: 1.15, 4: 1.10, 5: 1.35, 6: 1.20, 7: 1.30, 8: 1.40, 9: 1.0}
    severity_boost = {1: 0.85, 2: 0.92, 3: 1.0}

    effective_speed = amb_speed / (traffic * weather_mult.get(int(weather), 1.0) * 1.3) # 1.3 for urban
    effective_speed = max(effective_speed, 10)

    travel_time = (dist / effective_speed) * 60
    travel_time *= severity_boost.get(int(severity), 1.0)
    dispatch_delay = random.uniform(1.5, 3.0)

    eta = travel_time + dispatch_delay
    return round(max(eta, 2.0), 2)

async def allocate_ambulance(phone_number: str, accident_data: dict):
    """
    Smart Allocation Logic based on severity and ETA.
    """
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
            logger.warning("No available ambulances found in fleet.")
            return False

        # 2. Predict ETA for all available
        candidates = []
        for amb in available:
            eta = predict_eta(acc_lat, acc_lon, amb, severity, weather, hour)
            candidates.append({**amb, "predicted_eta": eta})
        
        # Sort by ETA
        candidates.sort(key=lambda x: x["predicted_eta"])
        
        selected_amb = None
        
        # 3. Apply Severity Rules
        if severity == 1:
            # Case 1: HIGH - Pick Fastest
            selected_amb = candidates[0]
            logger.info(f"High Severity: Allocated fastest {selected_amb['ambulance_id']}")
            
        elif severity == 2:
            # Case 2: MEDIUM - Best of top 2-3
            # For simplicity, we pick the first one but acknowledge the "balanced" rule
            selected_amb = candidates[0]
            logger.info(f"Medium Severity: Allocated {selected_amb['ambulance_id']}")
            
        else:
            # Case 3: LOW - Smart Preservation
            if len(candidates) > 1:
                nearest = candidates[0]
                second = candidates[1]
                
                # Rule: If 2nd is close enough (< 5 mins difference), take it to save the nearest
                if (second["predicted_eta"] - nearest["predicted_eta"]) < 5.0:
                    selected_amb = second
                    logger.info(f"Low Severity: Smart Allocation used {selected_amb['ambulance_id']} (saved {nearest['ambulance_id']})")
                else:
                    selected_amb = nearest
                    logger.info(f"Low Severity: 2nd too far, used nearest {selected_amb['ambulance_id']}")
            else:
                selected_amb = candidates[0]

        # 4. Finalize Dispatch
        if selected_amb:
            # Update DB
            await update_dispatch_status(phone_number, selected_amb["ambulance_id"], selected_amb["predicted_eta"])
            
            # Send WhatsApp
            msg = (
                f"🚑 *AMBULANCE DISPATCHED*\n\n"
                f"Ambulance *{selected_amb['ambulance_id']}* is on the way.\n"
                f"⏱️ Estimated Arrival: *{selected_amb['predicted_eta']} minutes*.\n\n"
                f"Please stay on the line and keep the patient calm."
            )
            await send_whatsapp_message(phone_number, msg)
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error in ambulance allocation: {e}")
        return False
