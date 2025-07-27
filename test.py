import ESL

con = ESL.ESLconnection("127.0.0.1", "8021", "eba1395137fb49d1")

if con.connected():
    print("✅ Connected to FreeSWITCH ESL interface!")

    con.events("plain", "ALL")

    while True:
        e = con.recvEvent()
        if e:
            print(f"\n📦 EVENT: {e.serialize()}")
else:
    print("❌ Failed to connect to FreeSWITCH.")
