import json
import redis
import time

# Constants
TO_AKKA_APPS_CHAN_2x = "to-akka-apps-redis-channel"

# Set up Redis connection (adjust host/port if needed)
r = redis.Redis(host="localhost", port=6379)


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


# Example usage
send_caption(
    meeting_id="8f9a5dd0bdae1033a275102c12a7040b22a3ef22-1753949880184",
    user_id="w_dsraz8xm8mhn",
    text="Hello World"
)
