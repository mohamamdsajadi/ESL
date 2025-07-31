import ESL
import json
import redis
import time

# Redis caption channel for BigBlueButton
TO_AKKA_APPS_CHAN_2x = "to-akka-apps-redis-channel"
r = redis.Redis(host="localhost", port=6379)

# Function to push transcript to BBB
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
                "transcriptId": f"{user_id}-{now}",
                "start": str(now),
                "end": str(now + 1500),
                "text": "",
                "transcript": text,
                "locale": locale,
                "result": True
            }
        }
    }

    r.publish(TO_AKKA_APPS_CHAN_2x, json.dumps(payload))
    print(f"[Caption Sent] {user_id=} {meeting_id=} {text=}")

# Connect to FreeSWITCH ESL
con = ESL.ESLconnection("127.0.0.1", "8021", "eba1395137fb49d1")

if not con.connected():
    print("❌ ESL connection failed.")
    exit(1)

print("✅ Connected to FreeSWITCH ESL")
con.events("plain", "CUSTOM")  # Only listen to CUSTOM events

# Event loop to listen for transcription responses
while True:
    e = con.recvEvent()
    if not e:
        continue

    if e.getHeader("Event-Name") != "CUSTOM":
        continue

    subclass = e.getHeader("Event-Subclass")

    if subclass == "mod_audio_fork::response":
        print("response subclass detected")
        raw_msg = e.getHeader("mod_audio_fork-response")
        uuid = e.getHeader("Unique-ID")

        try:
            data = json.loads(raw_msg)
            user_id = data.get("user_id")
            meeting_id = data.get("meeting_id")
            text = data.get("text")

            if user_id and meeting_id and text:
                print(user_id, meeting_id, text , "pushed")
                send_caption(meeting_id, user_id, text)
            else:
                print(f"[WARN] Missing fields in STT response: {raw_msg}")

        except Exception as err:
            print(f"[ERROR] Failed to parse STT response: {err}")
            print(f"[RAW] {raw_msg}")
