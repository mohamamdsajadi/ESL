import os
import time
import urllib.parse
import ESL

ESL_HOST = os.getenv("ESL_HOST", "127.0.0.1")
ESL_PORT = os.getenv("ESL_PORT", "8021")
ESL_PASS = os.getenv("ESL_PASS", "d5fa706c7fbac6aa")

WS_BASE = os.getenv("WS_BASE", "ws://46.245.79.23:9000/ws/audio")

def main():
    forked_uuids = set()

    while True:
        con = ESL.ESLconnection(ESL_HOST, ESL_PORT, ESL_PASS)
        if not con.connected():
            continue

        # Subscribe and filter server-side
        con.events("plain", "CUSTOM")
        con.filter("Event-Subclass", "conference::maintenance")

        print("Connected to ESL and listening for conference maintenance events")

        while con.connected():
            print("connection stablished.")
            e = con.recvEvent()
            if not e:
                print("BREAK")
                # connection dropped or timeout; break to reconnect
                break
            print("Event received.")

            event_name = e.getHeader("Event-Name")
            subclass   = e.getHeader("Event-Subclass")
            action     = e.getHeader("Action")
            uuid       = e.getHeader("Unique-ID")
            user_id    = e.getHeader("Caller-Caller-ID-Number")
            user_name  = e.getHeader("Caller-Caller-ID-Name")
            conf_name  = e.getHeader("variable_conference_name")
            speak      = e.getHeader("Speak")

            # Basic checks
            if event_name != "CUSTOM" or subclass != "conference::maintenance":
                print("Event received Not custom.")
                continue
            if not uuid or not user_id or not conf_name or not user_name:
                print("one of user conf or user name is not present" , user_id, user_name, conf_name)
                continue

            # BBB-style caller name often has "<user_id>-bbbID-<fullname>"
            try:
                user_name_clean = user_name.replace(f"{user_id}-bbbID-", "")
                print("user_name_clean=")
            except Exception:
                user_name_clean = user_name

            # URL-encode query params
            qs = urllib.parse.urlencode({
                "user_id": user_id,
                "meeting_id": conf_name,
                "user_name": user_name_clean
            })
            ws_url = f"{WS_BASE}?{qs}"

            # Decide when to start fork:
            # If you want "start on unmute", ignore Speak.
            # If you only want active talkers, keep the Speak == "true" condition.
            start_condition = (action == "unmute-member")
            # If you prefer your original logic: use start_condition = (action == "unmute-member" and speak == "true")

            stop_condition = action in ("mute-member", "del-member", "kick-member")

            if start_condition and uuid not in forked_uuids:
                fork_cmd = f"uuid_audio_fork {uuid} start {ws_url} mono 16000"
                res = con.bgapi(fork_cmd)
                print(f"[Fork Start] {uuid=} {user_id=} {conf_name=} => {res.getBody()}")
                forked_uuids.add(uuid)

            elif stop_condition and uuid in forked_uuids:
                stop_cmd = f"uuid_audio_fork {uuid} stop"
                res = con.bgapi(stop_cmd)
                print(f"[Fork Stop]  {uuid=} {user_id=} {conf_name=} => {res.getBody()}")
                forked_uuids.remove(uuid)

        # If we reach here, try to reconnect
        print("ESL disconnected, retrying...")
        time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    main()