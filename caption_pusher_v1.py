# transcription_pusher.py
import hashlib
import requests
from urllib.parse import urlencode
import time


class BBBTranscriptionPusher:
    def __init__(self, bbb_url, bbb_secret):
        self.bbb_url = bbb_url
        self.bbb_secret = bbb_secret
        self.seq_num = 0

    def generate_checksum(self, api_call, params):
        """Generate BBB API checksum"""
        query = urlencode(sorted(params.items()))
        data = f"{api_call}{query}{self.bbb_secret}"
        return hashlib.sha1(data.encode()).hexdigest()

    def send_caption(self, meeting_id, transcription, locale='en-US'):
        """Send caption/transcription to meeting"""
        self.seq_num += 1

        params = {
            'meetingID': meeting_id,
            'ownerID': 'transcription-bot',
            'locale': locale,
            'text': transcription,
            'seqNum': self.seq_num
        }

        checksum = self.generate_checksum('sendCaptionHistory', params)
        params['checksum'] = checksum

        try:
            response = requests.post(
                f"{self.bbb_url}/bigbluebutton/api/sendCaptionHistory",
                params=params
            )
            print(f"Caption sent: {transcription}")
            return response.text
        except Exception as e:
            print(f"Error sending caption: {e}")
            raise

    def stream_transcription(self, meeting_id):
        """Simulate streaming transcription"""
        test_messages = [
            "Welcome to the meeting.",
            "This is an automated transcription.",
            "The audio is being processed in real-time."
        ]

        for message in test_messages:
            self.send_caption(meeting_id, message)
            time.sleep(3)


# Usage
if __name__ == "__main__":
    pusher = BBBTranscriptionPusher(
        bbb_url='https://vcdemo.mparsict.com/bigbluebutton/',
        bbb_secret='GkYHKfLS4NvDss0LfXWDyUjRtcJ4H0s9RQdSPZkI18Y'
    )

    meeting_id = '15959'
    pusher.send_caption(meeting_id, "Hello, this is a test transcription!")