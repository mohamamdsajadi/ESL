from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
import time
import hashlib
import requests
import uuid
import xml.etree.ElementTree as ET
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


class CreateMeetingRequest(BaseModel):
    name: str
    moderator_name: str = "Moderator"

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


@app.post("/create_meeting")
def create_meeting(request: CreateMeetingRequest):

    meeting_id = str(uuid.uuid4())

    # -------------------------
    # 1. Create meeting
    # -------------------------

    create_params = {
        "name": request.name,
        "meetingID": meeting_id,
        "record": "false",
        "autoStartRecording": "false",
        "allowStartStopRecording": "true",
    }

    create_query = urlencode(create_params)

    create_checksum = hashlib.sha1(
        (
            "create"
            + create_query
            + BBB_SECRET
        ).encode("utf-8")
    ).hexdigest()

    create_url = (
        f"{BBB_URL}/api/create?"
        f"{create_query}"
        f"&checksum={create_checksum}"
    )

    try:
        response = requests.get(
            create_url,
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to BigBlueButton: {str(e)}"
        )

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        raise HTTPException(
            status_code=502,
            detail="Invalid response received from BigBlueButton"
        )

    if root.findtext("returncode") != "SUCCESS":
        raise HTTPException(
            status_code=400,
            detail={
                "message_key": root.findtext("messageKey"),
                "message": root.findtext("message"),
            }
        )
    print(root)

    # -------------------------
    # 2. Generate moderator join URL
    # -------------------------

    join_params = {
        "meetingID": meeting_id,
        "fullName": request.moderator_name,
        "role": "MODERATOR",
        "redirect": "true",
    }

    join_query = urlencode(join_params)

    join_checksum = hashlib.sha1(
        (
            "join"
            + join_query
            + BBB_SECRET
        ).encode("utf-8")
    ).hexdigest()

    join_url = (
        f"{BBB_URL}/api/join?"
        f"{join_query}"
        f"&checksum={join_checksum}"
    )

    # -------------------------
    # 3. Return meeting info
    # -------------------------

    return {
        "success": True,
        "meeting_id": meeting_id,
        "internal_meeting_id": root.findtext("internalMeetingID"),
        "conference_name": root.findtext("voiceBridge"),
        "meeting_name": request.name,
        "moderator_name": request.moderator_name,
        "join_url": join_url,
    }
