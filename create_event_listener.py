import redis
import threading
import json
import time

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Constants
REDIS_CHANNEL = "from-akka-apps-redis-channel"
VOICE_TO_MEETING_KEY = "bbb-transcription-manager_voiceToMeeting_"

def handle_meeting_created(payload):
    try:
        voice_conf = payload["body"]["voiceProp"]["voiceConf"]
        meeting_id = payload["body"]["meetingProp"]["intId"]

        # Store mapping in Redis
        r.set(f"{VOICE_TO_MEETING_KEY}{voice_conf}", meeting_id)
        print(f"[Meeting Created] voiceConf={voice_conf}  →  meetingId={meeting_id}")
    except Exception as e:
        print("[Error parsing MeetingCreatedEvtMsg]", e)

def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    print(f"✅ Subscribed to Redis channel: {REDIS_CHANNEL}")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
            if data.get("envelope", {}).get("name") == "MeetingCreatedEvtMsg":
                print("got the message ", data)
                handle_meeting_created(data["core"])
        except Exception as e:
            print("[Invalid Redis Message]", e)

# Run listener in background thread
threading.Thread(target=redis_listener, daemon=True).start()
