from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
import logging

from app.core.config import settings
from app.services.ai_service import generate_reply
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Endpoint for Meta to verify the webhook setup.
    Meta sends a GET request with specific challenge parameters.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    
    logger.error("Webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

async def process_whatsapp_message(user_phone_number: str, text_body: str):
    """
    Background task to generate and send reply
    """
    try:
        ai_response = await generate_reply(text_body)
        await send_whatsapp_message(to_number=user_phone_number, text=ai_response)
    except Exception as e:
        logger.error(f"Error in background processing: {e}")

# In-memory storage for deduplication (for production, use Redis or a database)
processed_message_ids = set()

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint to receive incoming WhatsApp messages.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON text")
    
    # Validation to ensure it's a WhatsApp page event
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Check if it contains messages
                if "messages" in value:
                    for message in value["messages"]:
                        # We only process text messages for now
                        if message.get("type") == "text":
                            msg_id = message.get("id")
                            
                            # Deduplicate webhook retries
                            if msg_id in processed_message_ids:
                                logger.info(f"Duplicate message picked up and ignored: {msg_id}")
                                continue
                            
                            # Add to processed set
                            processed_message_ids.add(msg_id)
                            # Simple cleanup to prevent continuous memory growth
                            if len(processed_message_ids) > 1000:
                                processed_message_ids.clear()
                                
                            user_phone_number = message["from"]
                            text_body = message["text"]["body"]
                            
                            logger.info(f"Received message from {user_phone_number}: {text_body}")
                            
                            # Process message in background to return 200 OK to Meta immediately
                            background_tasks.add_task(process_whatsapp_message, user_phone_number, text_body)
                            
        return {"status": "success"}

    raise HTTPException(status_code=404, detail="Not a valid WhatsApp payload")
