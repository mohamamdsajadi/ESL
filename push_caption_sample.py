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
meeting_id = "42676c17f7c107e9f7a830d24439dd97d9b05656-1766330592507"
user_id = "w_qx1ooacjuyfg"

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
