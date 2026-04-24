import pandas as pd
import numpy as np
import os

def generate_dummy_excel(output_path="Accidents_Mumbai.xlsx"):
    print(f"Generating dummy accident data at {output_path}...")
    np.random.seed(42)
    n_records = 500
    
    # Mumbai Bounding Box (approx)
    lat_range = (18.90, 19.30)
    lon_range = (72.75, 73.00)
    
    data = {
        "latitude": np.random.uniform(*lat_range, n_records),
        "longitude": np.random.uniform(*lon_range, n_records),
        "Accident_Severity": np.random.choice([1, 2, 3], n_records, p=[0.1, 0.3, 0.6]),
        "Weather_Conditions": np.random.randint(1, 10, n_records),
        "Light_Conditions": np.random.choice([1, 4, 5, 6, 7], n_records),
        "Road_Surface_Conditions": np.random.randint(1, 6, n_records),
        "Speed_limit": np.random.choice([30, 40, 50, 60, 80], n_records),
        "Number_of_Casualties": np.random.randint(1, 5, n_records),
        "Day_of_Week": np.random.randint(1, 8, n_records),
        "Road_Type": np.random.randint(1, 7, n_records),
        "Urban_or_Rural_Area": np.random.choice([1, 2], n_records),
        "Time": [f"{np.random.randint(0, 24):02d}:{np.random.randint(0, 60):02d}" for _ in range(n_records)]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    print("Dummy data generated successfully.")

if __name__ == "__main__":
    generate_dummy_excel()
