from fastapi import FastAPI, Request
from pydantic import BaseModel
import redis
import json
import time

app = FastAPI()

# Constants

# Pydantic model for input validation
class CaptionRequest(BaseModel):
    meeting_id: str
    user_id: str
    text: str

TO_AKKA_APPS_CHAN_2x = "to-akka-apps-redis-channel"
r = redis.Redis(host="localhost", port=6379)

# Caption sender function
def send_caption(meeting_id, user_id, text, locale="en-US"):

    now = int(time.time() * 1000)
    payload = {
        "envelope": {
            "name": "UpdateTranscriptPubMsg",
            "routing": {"meetingId": meeting_id, "userId": user_id},
            "timestamp": now
        },
        "core": {
            "header": {
                "name": "UpdateTranscriptPubMsg",
                "meetingId": meeting_id,
                "userId": user_id
            },
            "body": {
                "transcriptId": f"{user_id}-0",
                "start": "0",
                "end": "0",
                "text": "",
                "transcript": text,
                "locale": locale,
                "result": True
            }
        }
    }

    r.publish(TO_AKKA_APPS_CHAN_2x, json.dumps(payload))
    print("Caption sent to Redis.")

    r.publish(TO_AKKA_APPS_CHAN_2x, json.dumps(payload))
    print(f"[Caption Sent] {user_id=} {meeting_id=} {text=}")

# POST endpoint to receive transcript
@app.post("/caption")
async def push_caption(req: CaptionRequest):
    send_caption(req.meeting_id, req.user_id, req.text)
    return {"status": "ok", "message": "Caption pushed to Redis"}
