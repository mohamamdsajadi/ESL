import hashlib
import requests
from urllib.parse import urlencode


BBB_URL = "https://vcdemo.mparsict.com/bigbluebutton/api"
BBB_SECRET = "GkYHKfLS4NvDss0LfXWDyUjRtcJ4H0s9RQdSPZkI18Y"


def send_public_chat(meeting_id, message, user_name="System"):
    api_call = "sendChatMessage"

    params = {
        "meetingID": meeting_id,
        "message": message,
        "userName": user_name
    }

    # BBB requires checksum:
    # SHA1(apiCall + queryString + sharedSecret)
    query_string = urlencode(params)

    checksum_string = api_call + query_string + BBB_SECRET

    checksum = hashlib.sha1(
        checksum_string.encode("utf-8")
    ).hexdigest()

    url = f"{BBB_URL}/{api_call}"

    params["checksum"] = checksum

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    print(response.text)

    return response


if __name__ == "__main__":
    send_public_chat(
        meeting_id="",
        message="https://vcdemo.mparsict.com/bigbluebutton/api                           Analysis completed <button onclick=\"callAPI()\">Open Report</button>",
        user_name="Transcription Bot"
    )
