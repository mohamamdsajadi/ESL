import redis
import threading
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),  # log to console
        logging.FileHandler("meeting_listener.log")  # also log to file
    ]
)

logger = logging.getLogger("RedisListener")

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
REDIS_CHANNEL = "to-akka-apps-redis-channel"
VOICE_TO_MEETING_KEY = "bbb-transcription-manager_voiceToMeeting_"

def handle_meeting_created(payload):
    try:
        voice_conf = payload["body"]["voiceProp"]["voiceConf"]
        meeting_id = payload["body"]["meetingProp"]["intId"]
        r.set(f"{VOICE_TO_MEETING_KEY}{voice_conf}", meeting_id)
        logger.info(f"🟢 Meeting Created: voiceConf={voice_conf} → meetingId={meeting_id}")
    except Exception as e:
        logger.error("❌ Error parsing MeetingCreatedEvtMsg", exc_info=e)

def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    logger.info(f"✅ Subscribed to Redis channel: {REDIS_CHANNEL}")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
            if data.get("envelope", {}).get("name") == "MeetingCreatedEvtMsg":
                handle_meeting_created(data["core"])
        except Exception as e:
            logger.error("❌ Invalid Redis Message", exc_info=e)

# Start thread
threading.Thread(target=redis_listener, daemon=True).start()
