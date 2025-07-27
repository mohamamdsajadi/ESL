import ESL

con = ESL.ESLconnection("127.0.0.1", "8021", "eba1395137fb49d1")

if con.connected():
    print("connected")

    con.events("plain", "ALL")  # Subscribe to relevant events

    forked_uuids = set()

    while True:
        e = con.recvEvent()
        if not e:
            continue
        print(e.getHeader("Event-Name"))

        # Filter only CUSTOM events with conference::maintenance subclass
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
        user_name: str = e.getHeader("Caller-Caller-ID-Name").replace(user_id+"-bbbID-", "")
        meeting_id = e.getHeader("Caller-Destination-Number")  # bbb meeting ID
        speak = e.getHeader("Speak")  # "true" / "false"

        # Ensure required fields are present
        if not uuid or not user_id or not meeting_id:
            continue

        # ✅ User is unmuted — start audio fork
        if action == "unmute-member" and speak == "true" and uuid not in forked_uuids:
            ws_url = f"ws://46.245.79.23:9000/ws/audio?user_id={user_id}&meeting_id={meeting_id}&user_name={user_name}"
            fork_cmd = f"uuid_audio_fork {uuid} start {ws_url} mono 16000"
            con.api(fork_cmd)
            forked_uuids.add(uuid)
            print(f"[Fork Started] {user_id=} {meeting_id=} {uuid=}")

        # 🔴 User is muted — stop audio fork
        elif action == "mute-member" and speak == "false" and uuid in forked_uuids:
            stop_cmd = f"uuid_audio_fork {uuid} stop"
            con.api(stop_cmd)
            forked_uuids.remove(uuid)
            print(f"[Fork Stopped] {user_id=} {meeting_id=} {uuid=}")
