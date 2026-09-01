import ESL
from urllib.parse import urlencode, quote

con = ESL.ESLconnection("127.0.0.1", "8021", "d5fa706c7fbac6aa")

if con.connected():
    print("connected")

    con.events("plain", "ALL")

    forked_uuids = set()

    while True:
        e = con.recvEvent()
        if not e:
            continue

        print("*******************")
        print(e.getHeader("Event-Name"))
        print("------------------------")

        if e.getHeader("Event-Name") != "CUSTOM":
            continue

        subclass = e.getHeader("Event-Subclass")
        if subclass != "conference::maintenance":
            continue

        action = e.getHeader("Action")
        uuid = e.getHeader("Unique-ID")
        user_id = e.getHeader("Caller-Caller-ID-Number")

        if not user_id:
            continue

        user_name = e.getHeader("Caller-Caller-ID-Name").replace(
            user_id + "-bbbID-", ""
        )

        user_id = user_id.rsplit("_", 1)[0]

        conference_name = e.getHeader("Conference-Name")
        speak = e.getHeader("Speak")

        print("special log", conference_name, user_name, user_id)

        if not uuid or not user_id or not conference_name:
            print("no uuid or user_id or conference_name")
            continue

        # User is unmuted — start audio fork
        if action == "unmute-member" and speak == "true" and uuid not in forked_uuids:

            query_params = urlencode(
                {
                    "user_id": user_id,
                    "conference_name": conference_name,
                    "user_name": user_name,
                },
                quote_via=quote,
            )

            ws_url = (
                f"ws://46.245.79.23:9000/ws/transcribe?"
                f"{query_params}"
            )

            fork_cmd = f"uuid_audio_fork {uuid} start {ws_url} mono 16000"

            print("Fork command:", fork_cmd)

            res = con.bgapi(fork_cmd)
            print(res.getBody())

            forked_uuids.add(uuid)

            print(
                f"[Fork Started] "
                f"{user_id=} {user_name=} {conference_name=} {uuid=}"
            )

        # User is muted — stop audio fork
        elif action == "mute-member" and speak == "false" and uuid in forked_uuids:

            stop_cmd = f"uuid_audio_fork {uuid} stop"

            con.api(stop_cmd)
            forked_uuids.remove(uuid)

            print(
                f"[Fork Stopped] "
                f"{user_id=} {conference_name=} {uuid=}"
            )
