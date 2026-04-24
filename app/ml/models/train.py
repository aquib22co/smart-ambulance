"""
train.py — Mumbai Smart Ambulance Allocation
Model 1: ETA Prediction

Generates:
  - model.pkl        (trained GradientBoostingRegressor)
  - label_encoder.pkl (zone LabelEncoder)
  - model_meta.json  (features, metrics, version info)

Usage:
  python train.py --data path/to/Accidents_Mumbai.xlsx
  python train.py --data path/to/Accidents_Mumbai.xlsx --output ./models
"""

import argparse
import json
import os
import pickle
import warnings
from math import atan2, cos, radians, sin, sqrt

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
N_AMBULANCES = 30

MUMBAI_ZONES = {
    "South Mumbai":    {"lat": (19.05, 19.09), "lon": (72.82, 72.88)},
    "Central Mumbai":  {"lat": (19.09, 19.14), "lon": (72.83, 72.92)},
    "North Mumbai":    {"lat": (19.14, 19.22), "lon": (72.83, 72.94)},
    "Eastern Suburbs": {"lat": (19.07, 19.18), "lon": (72.88, 72.94)},
    "Western Suburbs": {"lat": (19.10, 19.21), "lon": (72.82, 72.87)},
}

FEATURE_COLS = [
    "distance_km",
    "severity",
    "weather",
    "light_conditions",
    "road_surface",
    "speed_limit",
    "num_casualties",
    "day_of_week",
    "road_type",
    "urban_rural",
    "hour_of_day",
    "is_rush_hour",
    "is_night",
    "is_weekend",
    "is_available",
    "fuel_level",
    "crew_experience",
    "amb_zone_enc",
]

MODEL_VERSION = "1.0.0"

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def parse_hour(t):
    try:
        if hasattr(t, "hour"):
            return t.hour + t.minute / 60
        return float(t) * 24
    except Exception:
        return 12.0


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — LOAD & CLEAN ACCIDENT DATA
# ─────────────────────────────────────────────────────────────────────────────
def load_accidents(path):
    print(f"[1/5] Loading accident data from: {path}")
    df = pd.read_excel(path)

    df = df.rename(
        columns={
            "latitude": "accident_lat",
            "longitude": "accident_lon",
            "Accident_Severity": "severity",
            "Weather_Conditions": "weather",
            "Light_Conditions": "light_conditions",
            "Road_Surface_Conditions": "road_surface",
            "Speed_limit": "speed_limit",
            "Number_of_Casualties": "num_casualties",
            "Day_of_Week": "day_of_week",
            "Road_Type": "road_type",
            "Urban_or_Rural_Area": "urban_rural",
        }
    )

    df["hour_of_day"] = df["Time"].apply(parse_hour)

    keep = [
        "accident_lat", "accident_lon", "severity", "weather",
        "light_conditions", "road_surface", "speed_limit",
        "num_casualties", "day_of_week", "road_type",
        "urban_rural", "hour_of_day",
    ]
    df = df[keep].dropna()
    print(f"       {len(df)} accident records loaded.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — SIMULATE AMBULANCE FLEET
# ─────────────────────────────────────────────────────────────────────────────
def generate_ambulance_fleet(n=N_AMBULANCES):
    zones = list(MUMBAI_ZONES.keys())
    rows = []
    for i in range(n):
        zone = zones[i % len(zones)]
        z = MUMBAI_ZONES[zone]
        rows.append(
            {
                "ambulance_id": f"AMB-{i+1:03d}",
                "zone": zone,
                "amb_lat": np.random.uniform(*z["lat"]),
                "amb_lon": np.random.uniform(*z["lon"]),
                "is_available": np.random.choice([1, 0], p=[0.9, 0.1]),
                "fuel_level": round(np.random.uniform(0.3, 1.0), 2),
                "crew_experience": np.random.randint(1, 10),
            }
        )
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — COMPUTE PHYSICS-BASED ETA (ground truth label)
# ─────────────────────────────────────────────────────────────────────────────
def compute_eta(row):
    """
    ETA (minutes) = travel_time + dispatch_delay

    travel_time depends on:
      - Distance (haversine)
      - Speed limit (from real data) + ambulance siren boost (+20%)
      - Time-of-day traffic multiplier (Mumbai rush hours)
      - Weather, light, road surface degradation factors
      - Urban vs rural congestion
      - Severity urgency (fatal cases drive faster)

    dispatch_delay = random 1.5–4.0 min (call receipt → wheels moving)
    """
    base_speed = min(row["speed_limit"], 60) if row["speed_limit"] > 0 else 40
    amb_speed = base_speed * 1.20  # siren boost

    # Time-of-day traffic multiplier (Mumbai-calibrated)
    h = row["hour_of_day"]
    if 8 <= h <= 10 or 17 <= h <= 20:
        traffic = np.random.uniform(1.6, 2.4)   # peak rush
    elif 12 <= h <= 14:
        traffic = np.random.uniform(1.2, 1.6)   # lunch
    elif h >= 22 or h <= 5:
        traffic = np.random.uniform(0.8, 1.0)   # night
    else:
        traffic = np.random.uniform(1.0, 1.4)   # normal

    weather_mult = {1: 1.0, 2: 1.25, 3: 1.15, 4: 1.10,
                    5: 1.35, 6: 1.20, 7: 1.30, 8: 1.40, 9: 1.0}
    light_mult   = {1: 1.0, 4: 1.10, 5: 1.20, 6: 1.05, 7: 1.15}
    surface_mult = {1: 1.0, 2: 1.15, 3: 1.50, 4: 1.40, 5: 1.60}
    severity_boost = {1: 0.85, 2: 0.92, 3: 1.0}  # 1=fatal → 15% faster

    effective_speed = amb_speed / (
        traffic
        * weather_mult.get(int(row["weather"]), 1.0)
        * light_mult.get(int(row["light_conditions"]), 1.0)
        * surface_mult.get(int(row["road_surface"]), 1.0)
        * (1.3 if row["urban_rural"] == 1 else 1.0)
    )
    effective_speed = max(effective_speed, 5)

    travel_time = (row["distance_km"] / effective_speed) * 60
    travel_time *= severity_boost.get(int(row["severity"]), 1.0)
    dispatch_delay = np.random.uniform(1.5, 4.0)

    eta = travel_time + dispatch_delay + np.random.normal(0, 0.5)
    return round(max(eta, 2.0), 2)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BUILD TRAINING DATASET
# ─────────────────────────────────────────────────────────────────────────────
def build_dataset(df_accidents, le):
    print("[2/5] Simulating ambulance fleet ...")
    ambulances = generate_ambulance_fleet(N_AMBULANCES)

    print("[3/5] Building (accident × ambulance) training pairs ...")
    records = []
    for _, acc in df_accidents.iterrows():
        n_candidates = np.random.randint(3, 7)
        candidates = ambulances.sample(n=n_candidates)

        for _, amb in candidates.iterrows():
            dist = haversine_km(
                acc["accident_lat"], acc["accident_lon"],
                amb["amb_lat"], amb["amb_lon"],
            )
            h = float(acc["hour_of_day"])
            dow = int(acc["day_of_week"])

            row = {
                # accident context
                "distance_km":      round(dist, 3),
                "severity":         int(acc["severity"]),
                "weather":          int(acc["weather"]),
                "light_conditions": int(acc["light_conditions"]),
                "road_surface":     int(acc["road_surface"]),
                "speed_limit":      float(acc["speed_limit"]),
                "num_casualties":   int(acc["num_casualties"]),
                "day_of_week":      dow,
                "road_type":        int(acc["road_type"]),
                "urban_rural":      int(acc["urban_rural"]),
                "hour_of_day":      h,
                "is_rush_hour":     int(8 <= h <= 10 or 17 <= h <= 20),
                "is_night":         int(h >= 22 or h <= 5),
                "is_weekend":       int(dow in [1, 7]),
                # ambulance context
                "is_available":     int(amb["is_available"]),
                "fuel_level":       float(amb["fuel_level"]),
                "crew_experience":  int(amb["crew_experience"]),
                "amb_zone_enc":     le.transform([amb["zone"]])[0],
                # for label computation
                "weather":          int(acc["weather"]),          # duplicate key OK (same value)
                "light_conditions": int(acc["light_conditions"]),
                "road_surface":     int(acc["road_surface"]),
                "speed_limit":      float(acc["speed_limit"]),
            }
            row["eta_minutes"] = compute_eta(row)
            records.append(row)

    df = pd.DataFrame(records)
    print(f"       {len(df):,} training rows generated.")
    print(f"       ETA → mean: {df['eta_minutes'].mean():.1f} min | "
          f"min: {df['eta_minutes'].min():.1f} | max: {df['eta_minutes'].max():.1f}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — TRAIN & EVALUATE
# ─────────────────────────────────────────────────────────────────────────────
def train(df):
    print("[4/5] Training GradientBoostingRegressor ...")
    X = df[FEATURE_COLS]
    y = df["eta_minutes"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.08,
        max_depth=5,
        min_samples_leaf=10,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5
    r2   = r2_score(y_test, y_pred)

    print(f"\n{'─'*40}")
    print(f"  MAE  : {mae:.3f} minutes")
    print(f"  RMSE : {rmse:.3f} minutes")
    print(f"  R²   : {r2:.4f}")
    print(f"{'─'*40}\n")

    metrics = {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)}
    return model, metrics


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — SAVE ARTIFACTS
# ─────────────────────────────────────────────────────────────────────────────
def save_artifacts(model, le, metrics, output_dir):
    print(f"[5/5] Saving artifacts to: {output_dir}/")
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, "model.pkl")
    le_path    = os.path.join(output_dir, "label_encoder.pkl")
    meta_path  = os.path.join(output_dir, "model_meta.json")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    with open(le_path, "wb") as f:
        pickle.dump(le, f)

    meta = {
        "version":        MODEL_VERSION,
        "model_type":     "GradientBoostingRegressor",
        "features":       FEATURE_COLS,
        "n_estimators":   300,
        "max_depth":      5,
        "learning_rate":  0.08,
        "metrics":        metrics,
        "zones":          list(MUMBAI_ZONES.keys()),
        "zone_encoding":  {zone: int(le.transform([zone])[0]) for zone in MUMBAI_ZONES},
        "feature_dtypes": {
            "distance_km": "float",
            "severity": "int (1=Fatal, 2=Serious, 3=Slight)",
            "weather": "int (1=Fine, 2=Rain, 5=Fog ...)",
            "light_conditions": "int (1=Daylight, 4=Dark-lit, 5=Dark-unlit ...)",
            "road_surface": "int (1=Dry, 2=Wet, 3=Snow ...)",
            "speed_limit": "float (km/h)",
            "num_casualties": "int",
            "day_of_week": "int (1=Sunday ... 7=Saturday)",
            "road_type": "int",
            "urban_rural": "int (1=Urban, 2=Rural)",
            "hour_of_day": "float (0.0–23.99)",
            "is_rush_hour": "int (0 or 1)",
            "is_night": "int (0 or 1)",
            "is_weekend": "int (0 or 1)",
            "is_available": "int (0 or 1)",
            "fuel_level": "float (0.0–1.0)",
            "crew_experience": "int (years)",
            "amb_zone_enc": "int (encoded from label_encoder.pkl)",
        },
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n  ✅  model.pkl        → {model_path}")
    print(f"  ✅  label_encoder.pkl → {le_path}")
    print(f"  ✅  model_meta.json  → {meta_path}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Train Mumbai ambulance ETA model")
    parser.add_argument(
        "--data",
        default="Accidents_Mumbai.xlsx",
        help="Path to the accidents Excel file",
    )
    parser.add_argument(
        "--output",
        default="./models",
        help="Output directory for model artifacts (default: ./models)",
    )
    args = parser.parse_args()

    print("\n======================================")
    print("  Mumbai Ambulance ETA Model — Train")
    print("======================================\n")

    # LabelEncoder for ambulance zones (fit before dataset build so we can use it)
    le = LabelEncoder()
    le.fit(list(MUMBAI_ZONES.keys()))

    df_accidents = load_accidents(args.data)
    df_train     = build_dataset(df_accidents, le)
    model, metrics = train(df_train)
    save_artifacts(model, le, metrics, args.output)

    print("\nTraining complete.\n")


if __name__ == "__main__":
    main()