import ESL

con = ESL.ESLconnection("127.0.0.1", "8021", "eba1395137fb49d1")

if con.connected():
    con.events("plain", "CHANNEL_BRIDGE")

    while True:
        e = con.recvEvent()
        if e:
            uuid = e.getHeader("Unique-ID")
            user_id = e.getHeader("variable_bbb_user_id")
            meeting_id = e.getHeader("variable_bbb_meeting_id")
            print("UUID", uuid, "USER_ID: ", user_id, "MEETING_ID", meeting_id)

            # Construct your audio stream target
            ws_url = f"ws://46.245.79.23:9000/ws/audio?userId={user_id}&meetingId={meeting_id}"
            fork_cmd = f"uuid_audio_fork {uuid} start {ws_url} mono 16000"

            # Send the command to FreeSWITCH
            con.api(fork_cmd)
            print("forked")
