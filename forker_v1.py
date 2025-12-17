import urllib.parse
import ESL

con = ESL.ESLconnection("127.0.0.1", "8021", "d5fa706c7fb49d1")

if con.connected():
    print("connected")
    con.events("plain", "CUSTOM")
    con.filter("Event-Subclass", "conference::maintenance")

    forked_uuids = set()

    while con.connected():
        e = con.recvEvent()
        if not e:
            continue

        if e.getHeader("Event-Name") != "CUSTOM" or e.getHeader("Event-Subclass") != "conference::maintenance":
            continue

        action = e.getHeader("Action")
        uuid   = e.getHeader("Unique-ID")
        user_id = e.getHeader("Caller-Caller-ID-Number")
        user_name = e.getHeader("Caller-Caller-ID-Name") or ""
        conf_name = e.getHeader("variable_conference_name")  # <-- use this, not Conference-Unique-ID

        if not uuid or not user_id or not conf_name:
            continue

        user_name_clean = user_name.replace(f"{user_id}-bbbID-", "")

        qs = urllib.parse.urlencode({
            "user_id": user_id,
            "meeting_id": conf_name,
            "user_name": user_name_clean
        })
        ws_url = f"ws://46.245.79.23:9000/ws/audio?{qs}"

        # Start fork on join or unmute (mic on)
        if action in ("add-member", "unmute-member") and uuid not in forked_uuids:
            res = con.bgapi(f"uuid_audio_fork {uuid} start {ws_url} mono 16000")
            print(res.getBody())
            forked_uuids.add(uuid)
            print(f"[Fork Started] user_id={user_id} conf={conf_name} uuid={uuid}")

        # Stop fork on mute or leave
        elif action in ("mute-member", "del-member", "kick-member") and uuid in forked_uuids:
            res = con.bgapi(f"uuid_audio_fork {uuid} stop")
            print(res.getBody())
            forked_uuids.remove(uuid)
            print(f"[Fork Stopped] user_id={user_id} conf={conf_name} uuid={uuid}")