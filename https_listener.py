from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import time
import hashlib
import requests
from urllib.parse import urlencode

app = FastAPI()


# --------------------------------
# Request models
# --------------------------------

class CaptionRequest(BaseModel):
    conf_name: str
    user_id: str
    text: str


class ChatRequest(BaseModel):
    conf_name: str
    message: str


# --------------------------------
# Redis configuration
# --------------------------------

REDIS_HOST = "localhost"
REDIS_PORT = 6379

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)


# --------------------------------
# BigBlueButton configuration
# --------------------------------

BBB_URL = "https://vcdemo.mparsict.com/bigbluebutton/"
BBB_SECRET = "GkYHKfLS4NvDss0LfXWDyUjRtcJ4H0s9RQdSPZkI18Y"

TRANSCRIPTION_BOT_NAME = "Transcription Bot"


# ============================================
# Caption
# ============================================

def send_caption(meeting_id, user_id, text, locale="en-US"):

    REDIS_CHANNEL = "to-akka-apps-redis-channel"

    transcript_id = f"{user_id}-{int(time.time() * 1000)}"
    timestamp = int(time.time() * 1000)

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

    redis_client.publish(
        REDIS_CHANNEL,
        json.dumps(payload)
    )

    print("Transcript message published successfully.")


@app.post("/caption")
async def push_caption(req: CaptionRequest):

    meeting_id = redis_client.get(
        f"bbb-transcription-manager_voiceToMeeting_{req.conf_name}"
    )

    if not meeting_id:
        raise HTTPException(
            status_code=404,
            detail="Meeting ID not found"
        )

    send_caption(
        meeting_id,
        req.user_id,
        req.text
    )

    return {
        "status": "ok",
        "message": "Caption pushed to Redis"
    }


# ============================================
# Public Chat
# ============================================

def send_public_chat(meeting_id: str, message: str):

    api_call = "sendChatMessage"

    params = {
        "meetingID": meeting_id,
        "message": message,
        "userName": TRANSCRIPTION_BOT_NAME
    }

    query_string = urlencode(params)

    checksum_source = (
        api_call
        + query_string
        + BBB_SECRET
    )

    checksum = hashlib.sha1(
        checksum_source.encode("utf-8")
    ).hexdigest()

    params["checksum"] = checksum

    response = requests.get(
        f"{BBB_URL}/{api_call}",
        params=params,
        timeout=10
    )

    response.raise_for_status()

    print(
        f"Public chat message sent: "
        f"{meeting_id=} {message=}"
    )

    return response.text


@app.post("/chat")
async def push_chat(req: ChatRequest):

    try:

        response = send_public_chat(
            req.conf_name,
            req.message
        )

        return {
            "status": "ok",
            "message": "Message sent to public chat",
            "sender": TRANSCRIPTION_BOT_NAME
        }

    except Exception as e:

        print("Failed to send public chat message:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
