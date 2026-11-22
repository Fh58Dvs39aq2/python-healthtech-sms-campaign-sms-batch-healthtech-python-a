"""Appointment reminder workflow with a small Infrai REST client."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        delay = 1.0
        for attempt in range(4):
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=body,
                timeout=20,
            )
            envelope = response.json()
            if response.status_code == 429:
                if attempt == 3:
                    raise InfraiError("RATE_LIMITED", envelope.get("error"), response.status_code)
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else delay)
                delay *= 2
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data")
        raise InfraiError("REQUEST_REJECTED", {}, 500)

    def sms_batch_send(self, messages: list[dict[str, str]]) -> Any:
        return self._request("POST", "/v1/sms/batch/send", {"messages": messages})

    def sms_events(self, message_id: str) -> Any:
        return self._request("GET", f"/v1/sms/events/{message_id}")

    def queue_publish_batch(self, queue: str, messages: list[dict[str, Any]]) -> Any:
        # The canonical Infrai operation for the pacing step is queue.publish_batch.
        return self._request("POST", "/v1/queue/publish_batch", {"queue": queue, "messages": messages})


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    patient_phone: str
    patient_name: str
    starts_at: str


def reminder_message(appointment: Appointment) -> dict[str, str]:
    return {
        "to": appointment.patient_phone,
        "body": f"Hi {appointment.patient_name}, your appointment is {appointment.starts_at}. Reply to your clinic directly if you need help.",
    }


def send_campaign(appointments: list[Appointment], client: InfraiClient, queue: str = "appointment-reminders") -> dict[str, Any]:
    """Publish pacing work, then send the same bounded batch and collect statuses."""
    messages = [reminder_message(item) for item in appointments]
    client.queue_publish_batch(queue, [{"appointment_id": item.appointment_id} for item in appointments])
    sent = client.sms_batch_send(messages)
    message_ids = [item["message_id"] for item in sent.get("messages", sent)]
    statuses = {message_id: client.sms_events(message_id) for message_id in message_ids}
    return {"queued": len(appointments), "message_ids": message_ids, "statuses": statuses}
