import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.healthtech_sms import Appointment, InfraiClient, send_campaign


parser = argparse.ArgumentParser(description="Send the appointment reminder campaign.")
parser.add_argument("--recipient", action="append", required=True, help="Recipient phone number (repeat twice).")
args = parser.parse_args()
if len(args.recipient) != 2:
    parser.error("provide exactly two --recipient values")

appointments = [
    Appointment("apt-104", args.recipient[0], "Mina", "Tuesday at 09:30"),
    Appointment("apt-105", args.recipient[1], "Jon", "Tuesday at 11:00"),
]
print(json.dumps(send_campaign(appointments, InfraiClient()), indent=2))
