from openai import AsyncOpenAI
from app.core.config import settings
import logging
import json
import re
from datetime import datetime, timezone
from app.services.memory_service import get_chat_history, add_message_to_session, save_accident_data

logger = logging.getLogger(__name__)

# Initialize the OpenAI (or Groq) client
# To use standard OpenAI, remove the base_url argument
client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """
You are a helpful triage assistant for a 'Rapid Care' smart ambulance system. 
Your goal is to gather the following details from the reporter:
- longitude
- latitude
- injured_count (number)
- accident_type
- conscious (yes/no)
- breathing_status (yes/no)
- bleeding_status (heavy/moderate/none)
- injury_type
- mobility (yes/no)
- weather (integer code 1-9)

WEATHER CODES:
1: Fine (no wind)
2: Rain
3: Snow
4: Fine + High wind
5: Rain + High wind
6: Fog or mist
7: Severe wind
8: Flooding
9: Unknown
Ask the user briefly about the weather conditions and map their answer to the closest code above.

RULES:
1. Keep questions VERY short and to the point. No medical jargon.
2. Ask ONE question at a time.
3. Give options (like yes/no) when possible.
4. Allow skipping optional questions.

CRITICAL OPTIMIZED FLOW:
If a CRITICAL condition is detected (e.g., unconscious, not breathing, heavy bleeding):
- You MUST SKIP the remaining optional questions (accident_type, injury_type, mobility, weather).
- HOWEVER, you CANNOT skip 'longitude', 'latitude', and 'injured_count'. Ask the user to send their WhatsApp location if they haven't already. You must gather these 3 fields even if it is a critical emergency.
- Once you have the 3 mandatory fields AND (either all fields OR a critical condition is met), stop asking questions.

WHEN YOU ARE READY TO DISPATCH (i.e. you have all info OR hit the critical flow with mandatory fields):
You MUST output a JSON block in your response containing the gathered data.
The JSON block MUST be formatted EXACTLY like this (use your gathered data):
```json
{
  "longitude": "...",
  "latitude": "...",
  "accident_type": "...",
  "injured_count": 2,
  "conscious": "no",
  "breathing_status": "yes",
  "bleeding_status": "heavy",
  "injury_type": "head injury",
  "mobility": "no",
  "weather": 1
}
```
If you haven't gathered enough details to dispatch yet, do NOT output the JSON block, just ask the next question.
"""

async def generate_reply(phone_number: str, user_message: str) -> str:
    """
    Generates a reply from the AI model based on the user's message and chat history.
    Extracts JSON if present and saves it to the database.
    """
    try:
        # 1. Add user message to DB
        await add_message_to_session(phone_number, "user", user_message)

        # 2. Get history
        history = await get_chat_history(phone_number)
        
        # 3. Build messages array
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b", # Switched to Groq standard model for compatibility
            messages=messages,
            max_tokens=300,
            temperature=0.2
        )
        
        # Handle case where model returns None or empty
        raw_content = response.choices[0].message.content
        if not raw_content:
            logger.warning("LLM returned an empty response. Using fallback.")
            ai_response_text = "Thank you. We are processing your request. Please hold on."
        else:
            ai_response_text = raw_content.strip()

            if not ai_response_text:
                ai_response_text = "Thank you. We are processing your request. Please hold on."

        # 4. Check for JSON block (more robust regex that handles optional 'json' tag)
        json_pattern = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
        match = json_pattern.search(ai_response_text)
        
        if match:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                # Add timestamp of accident when it was reported
                now = datetime.now()
                decimal_hour = now.hour + (now.minute / 60.0) + (now.second / 3600.0)
                data["timestamp_of_accident"] = round(decimal_hour, 2)
                
                # Save to database
                await save_accident_data(phone_number, data)
                
                # Strip JSON from response
                clean_response = ai_response_text.replace(match.group(0), "").strip()
                
                # Add a dispatch confirmation if the clean response is empty
                if not clean_response:
                    clean_response = "Thank you. An ambulance has been dispatched to your location immediately. Please stay calm."
                
                ai_response_text = clean_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON output: {e}")

        # Final safety check before sending
        if not ai_response_text or ai_response_text.strip() == "":
            ai_response_text = "Thank you for the information. We are processing it."

        # 5. Add assistant message to DB
        await add_message_to_session(phone_number, "assistant", ai_response_text)

        return ai_response_text
    except Exception as e:
        logger.error(f"Error generating AI reply: {e}")
        return "I'm having trouble connecting right now, but please send your location and details immediately so we can dispatch help."
