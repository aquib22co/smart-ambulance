import logging
from app.db.database import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_chat_history(phone_number: str) -> list:
    """
    Retrieves the chat history for a specific phone number from MongoDB.
    """
    try:
        db = get_db()
        if db is None:
            return []
            
        session = await db.chat_sessions.find_one({"phone_number": phone_number})
        if session and "messages" in session:
            return session["messages"]
        return []
    except Exception as e:
        logger.error(f"Error retrieving chat history for {phone_number}: {e}")
        return []

async def add_message_to_session(phone_number: str, role: str, content: str) -> bool:
    """
    Appends a new message to the user's session in MongoDB.
    Role should be 'user' or 'assistant'.
    """
    try:
        db = get_db()
        if db is None:
            return False
            
        message = {"role": role, "content": content}
        
        await db.chat_sessions.update_one(
            {"phone_number": phone_number},
            {"$push": {"messages": message}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error adding message to session for {phone_number}: {e}")
        return False

async def save_accident_data(phone_number: str, data: dict) -> bool:
    """
    Saves the final extracted JSON data to the accident_reports collection.
    """
    try:
        db = get_db()
        if db is None:
            return False
            
        report = {
            "phone_number": phone_number,
            "data": data,
            "status": "in-progress",
            "severity": data.get("severity")
        }
        
        await db.accident_reports.insert_one(report)
        logger.info(f"Accident data saved successfully for {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Error saving accident data for {phone_number}: {e}")
        return False

async def update_dispatch_status(phone_number: str, ambulance_id: str, eta: float) -> bool:
    """
    Updates the accident report with the allocated ambulance and ETA.
    Sets status to 'dispatched'.
    """
    try:
        db = get_db()
        if db is None:
            return False
            
        await db.accident_reports.update_one(
            {"phone_number": phone_number, "status": "in-progress"},
            {"$set": {
                "status": "dispatched",
                "allocated_ambulance": ambulance_id,
                "predicted_eta": eta,
                "dispatched_at": datetime.now()
            }}
        )
        logger.info(f"Report updated to dispatched for {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Error updating dispatch status for {phone_number}: {e}")
        return False
