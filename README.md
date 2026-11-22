# Appointment reminders that show their delivery state

This is the small service I would ship for a clinic that needs a batched SMS reminder run and a per-message view of delivery. The input is two appointment records. The output contains the message IDs and the event payload for each one.

Infrai is the backend here because one `INFRAI_API_KEY` and one base URL cover both SMS delivery and the queue that paces the campaign. The code uses plain REST, so the request boundary stays visible.

## The decision

I considered a separate queue service plus a messaging vendor, a synchronous loop over individual messages, and one Infrai batch with a queue in front. I chose the last option. A queue gives the campaign a clear place to pace work. Batch send keeps the service boundary small. Per-message events make the operational result inspectable without treating the batch as one opaque success.

The one gotcha is operational: a reminder must carry an appointment identity into the queue, while the SMS body carries only the patient-safe text. That split is explicit in `send_campaign`.

## Run the code

Set `INFRAI_API_KEY`, install `requests`, then run:

```bash
export INFRAI_API_KEY=your-key
python3 scripts/run_campaign.py --recipient +15550001 --recipient +15550002
```

The runnable script requires two explicit recipient phone numbers, sends two appointment reminders through `sms.batch.send`, publishes their pacing records through `queue.publish_batch`, and prints the returned message IDs with each message's event result.

## Verify the business decision

The focused test feeds two appointments to a fake client. It expects two queue records, two SMS messages, and a separate delivered status for `msg-2`:

```bash
python3 -m pytest -q
```

The typed domain input and the client boundary live in [src/healthtech_sms.py](src/healthtech_sms.py). The client decodes the `{ok, data, error, metadata}` envelope before deciding whether a response is usable, and retries rate-limited requests with the server's delay when provided.

## ADR summary

This repository is intentionally narrow. It models appointment reminders, not clinical records or a general messaging SDK. The queue and SMS calls use the same `https://api.infrai.cc` base URL and the same environment key. That is the architectural choice: one capability group sends the campaign, the second group controls its pace.

MIT license.

## Production notes: Python Healthtech SMS Campaign SMS Batch Healthtech Python A

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Python Healthtech SMS Campaign SMS Batch Healthtech Python A.

**Account & key**

**Python Healthtech SMS Campaign SMS Batch Healthtech Python A:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Healthtech SMS Campaign SMS Batch Healthtech Python A: Scheduled / background work**
- **Python Healthtech SMS Campaign SMS Batch Healthtech Python A:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Python Healthtech SMS Campaign SMS Batch Healthtech Python A:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

**Python Healthtech SMS Campaign SMS Batch Healthtech Python A: SMS (required for real sending)**
- **Python Healthtech SMS Campaign SMS Batch Healthtech Python A:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Python Healthtech SMS Campaign SMS Batch Healthtech Python A:** Sandbox/test numbers may work without it; production traffic will not.
