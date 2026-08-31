import redis
import json
import time

# -----------------------------
# Configuration
# -----------------------------
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHANNEL = "to-akka-apps-redis-channel"

# -----------------------------
# Runtime variables
# -----------------------------
meeting_id = "e1948961754f587b62331af1018b75fa68f23779-1787724622105"
user_id = "w_jmnfvlwkkibh"

transcript_id = f"{user_id}-{int(time.time() * 1000)}"
timestamp = int(time.time() * 1000)

# -----------------------------
# Redis connection
# -----------------------------
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

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
            "text": " okaysdsadasd",
            "transcript": "okayasdad okayss",
            "locale": "en-US",
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
