from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import redis
import json
import time
import hashlib
import requests
import uuid
import xml.etree.ElementTree as ET
import os
import html

from urllib.parse import urlencode


app = FastAPI()


# ============================================================
# Request models
# ============================================================

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


# ============================================================
# Redis configuration
# ============================================================

REDIS_HOST = "localhost"
REDIS_PORT = 6379

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)


# ============================================================
# BigBlueButton configuration
# ============================================================


BBB_BASE_URL = "https://vcdemo.mparsict.com/bigbluebutton/"
BBB_SECRET = "GkYHKfLS4NvDss0LfXWDyUjRtcJ4H0s9RQdSPZkI18Y"

if not BBB_SECRET:
    raise RuntimeError(
        "BBB_SECRET environment variable is not configured"
    )


# This must point to YOUR FastAPI application.
#
# Development example:
# http://vcdemo.mparsict.com:8000
#
# Production example behind nginx:
# https://vcdemo.mparsict.com
#
PUBLIC_APP_URL = os.getenv(
    "PUBLIC_APP_URL",
    "http://vcdemo.mparsict.com:8000"
)


TRANSCRIPTION_BOT_NAME = "Transcription Bot"


# ============================================================
# BBB helper functions
# ============================================================

def generate_checksum(
    api_call: str,
    query_string: str
) -> str:

    checksum_source = (
        api_call
        + query_string
        + BBB_SECRET
    )

    return hashlib.sha1(
        checksum_source.encode("utf-8")
    ).hexdigest()


def generate_join_url(
    meeting_id: str,
    full_name: str,
    role: str = "VIEWER"
) -> str:

    params = {
        "meetingID": meeting_id,
        "fullName": full_name,
        "role": role.upper(),
        "redirect": "true",
    }

    query_string = urlencode(params)

    checksum = generate_checksum(
        "join",
        query_string
    )

    return (
        f"{BBB_BASE_URL}/api/join?"
        f"{query_string}"
        f"&checksum={checksum}"
    )


# ============================================================
# Caption
# ============================================================

def send_caption(
    meeting_id,
    user_id,
    text,
    locale="en-US"
):

    REDIS_CHANNEL = "to-akka-apps-redis-channel"

    transcript_id = (
        f"{user_id}-"
        f"{int(time.time() * 1000)}"
    )

    timestamp = int(
        time.time() * 1000
    )

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

    print(
        "Transcript message published successfully."
    )


@app.post("/caption")
async def push_caption(
    req: CaptionRequest
):

    meeting_id = redis_client.get(
        "bbb-transcription-manager_"
        f"voiceToMeeting_{req.conf_name}"
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


# ============================================================
# Public Chat
# ============================================================

def send_public_chat(
    meeting_id: str,
    message: str
):

    api_call = "sendChatMessage"

    params = {
        "meetingID": meeting_id,
        "message": message,
        "userName": TRANSCRIPTION_BOT_NAME
    }

    query_string = urlencode(params)

    checksum = generate_checksum(
        api_call,
        query_string
    )

    params["checksum"] = checksum

    response = requests.get(
        f"{BBB_BASE_URL}/{api_call}",
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
async def push_chat(
    req: ChatRequest
):

    try:

        send_public_chat(
            req.conf_name,
            req.message
        )

        return {
            "status": "ok",
            "message": "Message sent to public chat",
            "sender": TRANSCRIPTION_BOT_NAME
        }

    except Exception as e:

        print(
            "Failed to send public chat message:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# CREATE MEETING
# ============================================================

@app.post("/create_meeting")
def create_meeting(
    request: CreateMeetingRequest
):

    meeting_id = str(
        uuid.uuid4()
    )

    # --------------------------------------------------------
    # 1. Create BBB meeting
    # --------------------------------------------------------

    create_params = {

        "name": request.name,

        "meetingID": meeting_id,

        "record": "false",

        "autoStartRecording": "false",

        "allowStartStopRecording": "true",
    }

    create_query = urlencode(
        create_params
    )

    create_checksum = generate_checksum(
        "create",
        create_query
    )

    create_url = (
        f"{BBB_BASE_URL}/api/create?"
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
            detail=(
                "Could not connect to "
                f"BigBlueButton: {str(e)}"
            )
        )

    # --------------------------------------------------------
    # Parse BBB XML
    # --------------------------------------------------------

    try:

        root = ET.fromstring(
            response.text
        )

    except ET.ParseError:

        raise HTTPException(
            status_code=502,
            detail=(
                "Invalid response received "
                "from BigBlueButton"
            )
        )


    if root.findtext(
        "returncode"
    ) != "SUCCESS":

        raise HTTPException(
            status_code=400,
            detail={
                "message_key":
                    root.findtext(
                        "messageKey"
                    ),

                "message":
                    root.findtext(
                        "message"
                    ),
            }
        )


    # --------------------------------------------------------
    # 2. Generate moderator URL
    # --------------------------------------------------------

    moderator_join_url = (
        generate_join_url(

            meeting_id=
                meeting_id,

            full_name=
                request.moderator_name,

            role="MODERATOR"
        )
    )


    # --------------------------------------------------------
    # 3. Create public/shareable invite URL
    # --------------------------------------------------------

    invite_url = (
        f"{PUBLIC_APP_URL}"
        f"/room/{meeting_id}"
    )


    # --------------------------------------------------------
    # 4. Store meeting information
    # --------------------------------------------------------

    room_key = (
        f"bbb-custom-room:"
        f"{meeting_id}"
    )

    redis_client.hset(
        room_key,

        mapping={
            "meeting_id":
                meeting_id,

            "meeting_name":
                request.name,

            "moderator_name":
                request.moderator_name,

            "internal_meeting_id":
                root.findtext(
                    "internalMeetingID"
                ) or "",

            "voice_bridge":
                root.findtext(
                    "voiceBridge"
                ) or "",

            "created_at":
                str(
                    int(time.time())
                )
        }
    )


    print(
        "Meeting created:",
        meeting_id
    )

    print(
        "Invite URL:",
        invite_url
    )


    # --------------------------------------------------------
    # 5. Response
    # --------------------------------------------------------

    return {

        "success": True,

        "meeting_id":
            meeting_id,

        "internal_meeting_id":
            root.findtext(
                "internalMeetingID"
            ),

        "conference_name":
            root.findtext(
                "voiceBridge"
            ),

        "meeting_name":
            request.name,

        "moderator_name":
            request.moderator_name,

        "moderator_join_url":
            moderator_join_url,

        "invite_url":
            invite_url,
    }


# ============================================================
# PUBLIC ROOM PAGE
# ============================================================

@app.get(
    "/room/{meeting_id}",
    response_class=HTMLResponse
)
def room_page(
    meeting_id: str
):

    room_key = (
        f"bbb-custom-room:"
        f"{meeting_id}"
    )

    room_data = redis_client.hgetall(
        room_key
    )


    if not room_data:

        raise HTTPException(
            status_code=404,
            detail="Meeting room not found"
        )


    meeting_name = html.escape(
        room_data.get(
            "meeting_name",
            "Meeting"
        )
    )


    safe_meeting_id = html.escape(
        meeting_id
    )


    return f"""
<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Join {meeting_name}
    </title>


    <style>

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family:
                Arial,
                sans-serif;

            background:
                #f5f6fa;

            display:
                flex;

            justify-content:
                center;

            align-items:
                center;

            min-height:
                100vh;
        }}


        .join-card {{

            width:
                420px;

            max-width:
                90%;

            background:
                white;

            padding:
                36px;

            border-radius:
                14px;

            box-shadow:
                0 8px 30px
                rgba(
                    0,
                    0,
                    0,
                    0.12
                );
        }}


        h1 {{

            margin-top:
                0;

            margin-bottom:
                8px;

            font-size:
                26px;
        }}


        .meeting-name {{

            color:
                #666;

            margin-bottom:
                28px;
        }}


        label {{

            display:
                block;

            margin-bottom:
                8px;

            font-weight:
                bold;
        }}


        input {{

            width:
                100%;

            padding:
                14px;

            border:
                1px solid #ccc;

            border-radius:
                7px;

            font-size:
                16px;

            margin-bottom:
                20px;

            outline:
                none;
        }}


        input:focus {{

            border-color:
                #514988;
        }}


        button {{

            width:
                100%;

            padding:
                14px;

            border:
                none;

            border-radius:
                7px;

            background:
                #514988;

            color:
                white;

            font-size:
                16px;

            font-weight:
                bold;

            cursor:
                pointer;
        }}


        button:hover {{

            background:
                #40386f;
        }}


        .footer {{

            text-align:
                center;

            color:
                #999;

            font-size:
                12px;

            margin-top:
                20px;
        }}

    </style>

</head>


<body>


<div class="join-card">

    <h1>
        Join Meeting
    </h1>


    <div class="meeting-name">
        {meeting_name}
    </div>


    <form
        method="post"
        action="/room/{safe_meeting_id}/join"
    >

        <label>
            Display name
        </label>


        <input
            type="text"
            name="full_name"
            placeholder="Enter your name"
            autocomplete="name"
            required
        >


        <button type="submit">
            Join Meeting
        </button>

    </form>


    <div class="footer">
        Intelligent Meeting Platform
    </div>

</div>


</body>

</html>
"""


# ============================================================
# JOIN SHARED ROOM
# ============================================================

@app.post(
    "/room/{meeting_id}/join"
)
def join_shared_room(
    meeting_id: str,
    full_name: str = Form(...)
):

    # --------------------------------------------------------
    # Check that this room was created by our API
    # --------------------------------------------------------

    room_key = (
        f"bbb-custom-room:"
        f"{meeting_id}"
    )

    room_data = redis_client.hgetall(
        room_key
    )


    if not room_data:

        raise HTTPException(
            status_code=404,
            detail="Meeting room not found"
        )


    full_name = full_name.strip()


    if not full_name:

        raise HTTPException(
            status_code=400,
            detail="Display name is required"
        )


    if len(full_name) > 100:

        raise HTTPException(
            status_code=400,
            detail="Display name is too long"
        )


    # --------------------------------------------------------
    # Generate a VIEWER URL for this specific participant
    # --------------------------------------------------------

    join_url = generate_join_url(

        meeting_id=
            meeting_id,

        full_name=
            full_name,

        role=
            "VIEWER"
    )


    print(
        f"Joining meeting: "
        f"{meeting_id=} "
        f"{full_name=}"
    )


    # --------------------------------------------------------
    # Redirect browser to BBB
    # --------------------------------------------------------

    return RedirectResponse(
        url=join_url,
        status_code=303
    )
