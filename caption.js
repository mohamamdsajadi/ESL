const BigBlueButtonGW = require('./lib/bbb-gw');
const C = require('./lib/Constants');

const bbbGW = new BigBlueButtonGW();

function sendCaption(meetingId, userId, text, locale = 'en-US') {
  const payload = {
    envelope: {
      name: 'UpdateTranscriptPubMsg',
      routing: { meetingId, userId },
      timestamp: Date.now(),
    },
    core: {
      header: {
        name: 'UpdateTranscriptPubMsg',
        meetingId,
        userId,
      },
      body: {
        transcriptId: userId + '-0',
        start: '0',
        end: '0',
        text: '',
        transcript: text,
        locale,
        result: true,
      },
    },
  };

  // Publish to the same Redis channel as the controller
  bbbGW.publish(JSON.stringify(payload), C.TO_AKKA_APPS_CHAN_2x);
}

// Example usage
sendCaption('8f9a5dd0bdae1033a275102c12a7040b22a3ef22-1753909104959', 'w_5bt9yyqttlbb', 'Hello World');
