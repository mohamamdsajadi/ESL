import ESL

con = ESL.ESLconnection("127.0.0.1", "8021", "eba1395137fb49d1")

if con.connected():
    print("connected")

    # Subscribe to all events for testing — later you can narrow it down
    con.events("plain", "ALL")

    forked_uuids = set()  # prevent duplicate forks

    while True:
        e = con.recvEvent()
        if e:
            event_name = e.getHeader("Event-Name")
            print("EVNT: ", event_name)
            uuid = e.getHeader("Unique-ID")

            # Trigger only for voice events and not already forked
            if event_name in ["RECV_RTCP_AUDIO", "RECV_SILENCE_END"] and uuid not in forked_uuids:
                user_id = e.getHeader("variable_bbb_user_id")
                meeting_id = e.getHeader("variable_bbb_meeting_id")

                if user_id and meeting_id:
                    print("UUID", uuid, "USER_ID:", user_id, "MEETING_ID:", meeting_id)

                    ws_url = f"ws://46.245.79.23:9000/ws/audio?userId={user_id}&meetingId={meeting_id}"
                    fork_cmd = f"uuid_audio_fork {uuid} start {ws_url} mono 16000"

                    con.api(fork_cmd)
                    forked_uuids.add(uuid)
                    print("Forked audio for UUID:", uuid)
