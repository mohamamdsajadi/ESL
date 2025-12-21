from fastapi import FastAPI, Request
from pydantic import BaseModel
import redis
import json
import time

app = FastAPI()

# Constants

# Pydantic model for input validation
class CaptionRequest(BaseModel):
    conf_name: str
    user_id: str
    text: str

REDIS_HOST = "localhost"
REDIS_PORT = 6379
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)
# Caption sender function
def send_caption(meeting_id, user_id, text, locale="en-US"):
    # -----------------------------
    # Configuration
    # -----------------------------

    REDIS_CHANNEL = "to-akka-apps-redis-channel"

    # -----------------------------
    # Runtime variables
    # -----------------------------

    transcript_id = f"{user_id}-{int(time.time() * 1000)}"
    timestamp = int(time.time() * 1000)

    # -----------------------------
    # Redis connection
    # -----------------------------


    # -----------------------------
    # Message payload
    # -----------------------------
    payload = {
        "envelope": {
            "name": "UpdateTranscriptPubMsg",
            "routing": {
                "meetingId": meeting_id,
                "userId": user_id
            },
            "timestamp": timestamp
        },
        "core": {
            "header": {
                "name": "UpdateTranscriptPubMsg",
                "meetingId": meeting_id,
                "userId": user_id
            },
            "body": {
                "transcriptId": transcript_id,
                "start": 4,
                "end": 4,
                "text": "",
                "transcript": text,
                "locale": locale,
                "result": False
            }
        }
    }

    # -----------------------------
    # Publish to BigBlueButton Akka
    # -----------------------------
    redis_client.publish(
        REDIS_CHANNEL,
        json.dumps(payload)
    )

    print("Transcript message published successfully.")

# POST endpoint to receive transcript
@app.post("/caption")
async def push_caption(req: CaptionRequest):
    meeting_id = redis_client.get(f"bbb-transcription-manager_voiceToMeeting_{req.conf_name}")
    if isinstance(meeting_id, bytes):
        meeting_id = meeting_id.decode("utf-8")
    send_caption(meeting_id, req.user_id, req.text)
    return {"status": "ok", "message": "Caption pushed to Redis"}


