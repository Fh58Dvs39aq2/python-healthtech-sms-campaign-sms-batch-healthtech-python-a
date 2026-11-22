from src.healthtech_sms import Appointment, reminder_message, send_campaign
from src.healthtech_sms import InfraiClient, InfraiError
from unittest.mock import Mock

import pytest
import subprocess
import sys
from pathlib import Path


def test_documented_script_imports():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_campaign.py"
    result = subprocess.run([sys.executable, "-I", str(script), "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("exhausted", [False, True])
def test_unsuccessful_rate_limit_envelopes_retry(monkeypatch, exhausted):
    limited = Mock(status_code=429, headers={"Retry-After": "2"})
    limited.json.return_value = {"ok": False, "error": {"code": "RATE_LIMITED"}}
    success = Mock(status_code=200)
    success.json.return_value = {"ok": True, "data": {"accepted": 2}}
    request = Mock(side_effect=[limited] * 4 if exhausted else [limited, success])
    sleep = Mock()
    monkeypatch.setattr("src.healthtech_sms.requests.request", request)
    monkeypatch.setattr("src.healthtech_sms.time.sleep", sleep)
    client = InfraiClient(key="test")
    if exhausted:
        with pytest.raises(InfraiError) as error:
            client.queue_publish_batch("test", [])
        assert error.value.status == 429
        assert request.call_count == 4
        assert sleep.call_count == 3
    else:
        assert client.queue_publish_batch("test", []) == {"accepted": 2}
        sleep.assert_called_once_with(2.0)
    assert all(call.kwargs["headers"] == request.call_args.kwargs["headers"] for call in request.call_args_list)


class FakeClient:
    def __init__(self):
        self.queued = None
        self.sent = None

    def queue_publish_batch(self, queue, messages):
        self.queued = (queue, messages)
        return {"accepted": len(messages)}

    def sms_batch_send(self, messages):
        self.sent = messages
        return {"messages": [{"message_id": "msg-1"}, {"message_id": "msg-2"}]}

    def sms_events(self, message_id):
        return {"message_id": message_id, "status": "delivered"}


def test_campaign_paces_and_returns_per_message_status():
    appointments = [
        Appointment("a-1", "+15550001", "Ari", "09:00"),
        Appointment("a-2", "+15550002", "Bo", "10:00"),
    ]
    client = FakeClient()

    result = send_campaign(appointments, client)

    assert client.queued[0] == "appointment-reminders"
    assert client.queued[1] == [{"appointment_id": "a-1"}, {"appointment_id": "a-2"}]
    assert client.sent[0] == reminder_message(appointments[0])
    assert result["message_ids"] == ["msg-1", "msg-2"]
    assert result["statuses"]["msg-2"]["status"] == "delivered"
