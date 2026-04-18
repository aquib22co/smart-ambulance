from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize the OpenAI (or Groq) client
# To use standard OpenAI, remove the base_url argument
client = AsyncOpenAI(
    api_key=settings.AI_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

async def generate_reply(user_message: str) -> str:
    """
    Generates a reply from the AI model based on the user's message.
    """
    try:
        response = await client.chat.completions.create(
            # Switch to another model if needed. Groq uses "llama3-70b-8192" 
            # or the user requested string: "openai/gpt-oss-120b"
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful triage assistant for a 'Rapid Care' smart ambulance system. "
                        "When users report an accident, quickly gather details about the location, "
                        "type of accident, and severity. Keep your responses short and to the point."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating AI reply: {e}")
        return "I'm having trouble connecting right now, but please send your location and details immediately so we can dispatch help."
