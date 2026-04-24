from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
import logging
from app.services.memory_service import get_dispatch_by_id

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/track/{report_id}", response_class=HTMLResponse)
async def get_tracking_page(request: Request, report_id: str):
    report = await get_dispatch_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Tracking session not found")
    
    # We will embed the tracking data into the HTML for simplicity, 
    # or the JS can fetch it from an API. Let's do a simple embed for now.
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Live Tracking | Smart Ambulance</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #ff3b30;
                --dark: #1c1c1e;
                --glass: rgba(255, 255, 255, 0.9);
            }}
            body, html {{
                margin: 0;
                padding: 0;
                height: 100%;
                font-family: 'Inter', sans-serif;
                background: #000;
            }}
            #map {{
                height: 100%;
                width: 100%;
                z-index: 1;
            }}
            .overlay {{
                position: absolute;
                top: 20px;
                left: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            }}
            .card {{
                background: var(--glass);
                backdrop-filter: blur(10px);
                padding: 15px 20px;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                border: 1px solid rgba(255,255,255,0.2);
                pointer-events: auto;
                max-width: 400px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 4px 12px;
                background: var(--primary);
                color: white;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                margin-bottom: 8px;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
                100% {{ opacity: 1; }}
            }}
            h1 {{ margin: 0; font-size: 1.2rem; color: var(--dark); }}
            p {{ margin: 5px 0 0; color: #666; font-size: 0.9rem; }}
            .eta-box {{
                margin-top: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .eta-value {{
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--primary);
            }}
            .eta-label {{ font-size: 0.8rem; color: #888; }}
            
            /* Custom Map Markers */
            .ambulance-icon {{
                font-size: 24px;
                filter: drop-shadow(0 0 5px rgba(255,59,48,0.5));
            }}
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="card">
                <div class="status-badge">Live Tracking</div>
                <h1>Ambulance {report.get('allocated_ambulance')}</h1>
                <p>Heading to your location</p>
                <div class="eta-box">
                    <div>
                        <div class="eta-value">{report.get('predicted_eta')} min</div>
                        <div class="eta-label">Estimated Arrival</div>
                    </div>
                </div>
            </div>
        </div>
        <div id="map"></div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            const ambLat = {report.get('ambulance_lat')};
            const ambLon = {report.get('ambulance_lon')};
            const accLat = {report.get('accident_lat')};
            const accLon = {report.get('accident_lon')};

            // Initialize map
            const map = L.map('map').setView([ambLat, ambLon], 13);

            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap contributors'
            }}).addTo(map);

            // Icons
            const ambulanceIcon = L.divIcon({{
                html: '<div class="ambulance-icon">🚑</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }});

            const accidentIcon = L.divIcon({{
                html: '<div class="ambulance-icon">📍</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }});

            // Markers
            const ambMarker = L.marker([ambLat, ambLon], {{icon: ambulanceIcon}}).addTo(map);
            const accMarker = L.marker([accLat, accLon], {{icon: accidentIcon}}).addTo(map);

            // Fit bounds
            const bounds = L.latLngBounds([ambLat, ambLon], [accLat, accLon]);
            map.fitBounds(bounds, {{padding: [50, 50]}});

            // Draw route line
            const line = L.polyline([[ambLat, ambLon], [accLat, accLon]], {{
                color: '#ff3b30',
                weight: 3,
                opacity: 0.5,
                dashArray: '10, 10'
            }}).addTo(map);

            // Simple simulation of movement
            let progress = 0;
            const duration = 1000 * 60 * {report.get('predicted_eta') or 10}; // Total ETA in ms
            const step = 0.001; // Movement per interval
            
            function moveAmbulance() {{
                if (progress < 1) {{
                    progress += 0.005; // Simulate faster for demo
                    const currentLat = ambLat + (accLat - ambLat) * progress;
                    const currentLon = ambLon + (accLon - ambLon) * progress;
                    
                    ambMarker.setLatLng([currentLat, currentLon]);
                    
                    // Update bounds occasionally
                    if (Math.random() > 0.95) map.panTo([currentLat, currentLon]);
                    
                    setTimeout(moveAmbulance, 1000);
                }}
            }}

            moveAmbulance();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
