import ESL
from urllib.parse import urlencode


# ==========================================
# CONFIG
# ==========================================

ESL_HOST = "127.0.0.1"
ESL_PORT = "8021"
ESL_PASSWORD = "d5fa706c7fbac6aa"

TRANSCRIPTION_WS = "ws://46.245.79.23:9000/ws/transcribe"


# ==========================================
# ESL CONNECTION
# ==========================================

con = ESL.ESLconnection(
    ESL_HOST,
    ESL_PORT,
    ESL_PASSWORD
)

if not con.connected():
    raise RuntimeError("Could not connect to FreeSWITCH ESL")

print("========================================")
print("ESL CONNECTED")
print("========================================")


# فقط CUSTOM eventها را بگیر
con.events("plain", "ALL")


# UUID هایی که روی آنها audio fork فعال کرده‌ایم
forked_uuids = set()


# ==========================================
# START AUDIO FORK
# ==========================================

def start_audio_fork(
    uuid,
    user_id,
    user_name,
    conference_name
):
    if uuid in forked_uuids:
        print(
            "AUDIO FORK ALREADY TRACKED:",
            uuid
        )
        return

    params = urlencode({
        "user_id": user_id,
        "conference_name": conference_name,
        "user_name": user_name,
    })

    ws_url = (
        f"{TRANSCRIPTION_WS}"
        f"?{params}"
    )

    fork_cmd = (
        f"uuid_audio_fork {uuid} "
        f"start {ws_url} mono 16000 {{}}"
    )

    print("")
    print("========================================")
    print("STARTING AUDIO FORK")
    print("========================================")
    print("UUID:", uuid)
    print("USER ID:", user_id)
    print("USER NAME:", user_name)
    print("CONFERENCE:", conference_name)
    print("WS URL:", ws_url)
    print("COMMAND:", fork_cmd)

    con.api(f"uuid_audio_fork {uuid} stop")

    res = con.api(fork_cmd)

    if not res:
        print("AUDIO FORK ERROR: no response")
        return

    body = res.getBody() or ""

    print("AUDIO FORK RESULT:", repr(body))

    # اگر media bug از قبل وجود داشته باشد
    if "bug already attached" in body.lower():
        print(
            "BUG ALREADY ATTACHED."
            " STOPPING OLD FORK AND RETRYING..."
        )

        stop_res = con.api(
            f"uuid_audio_fork {uuid} stop"
        )

        if stop_res:
            print(
                "OLD FORK STOP RESULT:",
                repr(stop_res.getBody())
            )

        retry_res = con.api(fork_cmd)

        if not retry_res:
            print("RETRY FAILED: no response")
            return

        retry_body = retry_res.getBody() or ""

        print(
            "AUDIO FORK RETRY RESULT:",
            repr(retry_body)
        )

        if retry_body.startswith("-ERR"):
            print(
                "!!! AUDIO FORK RETRY FAILED !!!"
            )
            return

        forked_uuids.add(uuid)

        print(
            ">>> AUDIO FORK STARTED AFTER RETRY:",
            uuid
        )

        return

    if body.startswith("-ERR"):
        print("")
        print(
            "!!! AUDIO FORK FAILED !!!",
            body
        )
        return

    forked_uuids.add(uuid)

    print("")
    print(
        ">>> AUDIO FORK STARTED:",
        uuid
    )


# ==========================================
# STOP AUDIO FORK
# ==========================================

def stop_audio_fork(uuid):
    if not uuid:
        return

    print("")
    print(
        ">>> STOPPING AUDIO FORK:",
        uuid
    )

    res = con.api(
        f"uuid_audio_fork {uuid} stop"
    )

    if res:
        print(
            "STOP RESULT:",
            repr(res.getBody())
        )

    forked_uuids.discard(uuid)

    print(
        ">>> AUDIO FORK REMOVED:",
        uuid
    )


# ==========================================
# EVENT LOOP
# ==========================================

while True:
    try:
        e = con.recvEvent()

        if not e:
            continue

        event_name = e.getHeader(
            "Event-Name"
        )

        if event_name != "CUSTOM":
            continue

        subclass = e.getHeader(
            "Event-Subclass"
        )

        # فقط event های conference BBB
        if subclass != "conference::maintenance":
            continue

        action = e.getHeader(
            "Action"
        )

        uuid = e.getHeader(
            "Unique-ID"
        )

        raw_user_id = e.getHeader(
            "Caller-Caller-ID-Number"
        )

        caller_name = e.getHeader(
            "Caller-Caller-ID-Name"
        )

        conference_name = e.getHeader(
            "Conference-Name"
        )

        speak = e.getHeader(
            "Speak"
        )

        talking = e.getHeader(
            "Talking"
        )

        print("")
        print("----------------------------------------")
        print(
            "EVENT:",
            f"action={action!r}",
            f"speak={speak!r}",
            f"talking={talking!r}",
            f"uuid={uuid!r}"
        )

        # بعضی event ها caller id ندارند
        if not raw_user_id:
            print(
                "SKIP: no Caller-Caller-ID-Number"
            )
            continue

        if not uuid:
            print(
                "SKIP: no UUID"
            )
            continue

        if not conference_name:
            print(
                "SKIP: no Conference-Name"
            )
            continue

        # ==================================
        # USER ID / USER NAME
        # ==================================

        user_id = raw_user_id

        if caller_name:
            prefix = (
                raw_user_id
                + "-bbbID-"
            )

            user_name = caller_name.replace(
                prefix,
                ""
            )
        else:
            user_name = ""

        # نمونه:
        # w_eb6gdppkypxl_123
        # ->
        # w_eb6gdppkypxl

        if "_" in user_id:
            user_id = user_id.rsplit(
                "_",
                1
            )[0]

        print(
            "USER:",
            f"user_id={user_id!r}",
            f"user_name={user_name!r}",
            f"conference={conference_name!r}"
        )

        # ==================================
        # START
        # ==================================
        #
        # اولین بار که کاربر واقعاً شروع
        # به صحبت می‌کند WebSocket را باز کن.
        #
        # روی stop-talking آن را نبند.
        #
        # ==================================

        if action == "start-talking":

            if uuid in forked_uuids:
                print(
                    "Fork already active.",
                    "No new connection."
                )
                continue

            start_audio_fork(
                uuid=uuid,
                user_id=user_id,
                user_name=user_name,
                conference_name=conference_name
            )

            continue

        # ==================================
        # STOP TALKING
        # ==================================
        #
        # IMPORTANT:
        # WebSocket را اینجا نبند.
        #
        # ==================================

        if action == "stop-talking":
            print(
                "User stopped talking.",
                "Keeping audio fork alive."
            )

            continue

        # ==================================
        # MUTE / LEAVE
        # ==================================

        if action in (
            "mute-member",
            "del-member"
        ):
            if uuid in forked_uuids:
                stop_audio_fork(uuid)
            else:
                print(
                    "No tracked fork to stop:",
                    uuid
                )

            continue

    except KeyboardInterrupt:
        print("")
        print("Stopping listener...")

        for active_uuid in list(
            forked_uuids
        ):
            try:
                stop_audio_fork(
                    active_uuid
                )
            except Exception as exc:
                print(
                    "Cleanup error:",
                    active_uuid,
                    repr(exc)
                )

        break

    except Exception as exc:
        print("")
        print(
            "MAIN LOOP ERROR:",
            type(exc).__name__,
            repr(exc)
        )
