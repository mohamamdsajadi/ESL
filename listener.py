import asyncio
import websockets
import json
import redis
import time

# Redis channel used by BigBlueButton
TO_AKKA_APPS_CHAN_2x = "to-akka-apps-redis-channel"

# Set up Redis connection
r = redis.Redis(host="localhost", port=6379)


# Caption sender (your original function with timestamp support)
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


# WebSocket listener for STT server responses
async def listen_to_stt_server():
    uri = "ws://46.245.79.23:9000/ws/audio"

    async with websockets.connect(uri) as websocket:
        print(f"[Connected to STT Server at {uri}]")

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                # Expecting: { "user_id": ..., "meeting_id": ..., "text": ... }
                user_id = data.get("user_id")
                meeting_id = data.get("meeting_id")
                text = data.get("text")

                if user_id and meeting_id and text:
                    send_caption(meeting_id, user_id, text)
                else:
                    print(f"[WARN] Missing fields in message: {data}")

            except Exception as e:
                print(f"[ERROR] {e}")
                await asyncio.sleep(2)  # Backoff on failure


# Run the listener
asyncio.run(listen_to_stt_server())
