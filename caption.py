import json
import time
import redis

# Adjust host/port if your Redis server uses different values
r = redis.Redis(host="127.0.0.1", port=6379)

meeting_id = "8f9a5dd0bdae1033a275102c12a7040b22a3ef22-1753867571123"
user_id = "w_1epve9s5bfus"
locale = "en-US"
caption_text = "Hello from a Python script!"

start_ms = int(time.time() * 1000)       # example timestamp
end_ms = start_ms + 2000                 # example end time

message = {
    "envelope": {
        "name": "UpdateTranscriptPubMsg",
        "routing": {"meetingId": meeting_id, "userId": user_id},
        "timestamp": int(time.time() * 1000),
    },
    "core": {
        "header": {
            "name": "UpdateTranscriptPubMsg",
            "meetingId": meeting_id,
            "userId": user_id,
        },
        "body": {
            "transcriptId": f"{user_id}-{start_ms}",
            "start": str(start_ms),
            "end": str(end_ms),
            "text": caption_text,
            "transcript": caption_text,
            "locale": locale,
            "result": True,
        },
    },
}

channel = "to-akka-apps-redis-channel"
r.publish(channel, json.dumps(message))
