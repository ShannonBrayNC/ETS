import random
import uuid
from datetime import datetime, timedelta


random.seed(42)



def generate_ticket_events(count: int):
    base = datetime.utcnow()
    events = []

    for i in range(count):
        events.append(
            {
                "schemaVersion": "ets.evidence.v0.1",
                "eventId": str(uuid.uuid4()),
                "correlationId": f"TICKET-{i // 5}",
                "sequence": i,
                "timestamp": (base + timedelta(seconds=i)).isoformat(),
                "actor": {
                    "type": "service",
                    "id": "opshelm",
                },
                "action": "ticket.update",
                "eventType": "state_change",
                "inputs": {
                    "priority": random.choice(["low", "medium", "high"])
                },
                "outputs": {
                    "status": random.choice(["open", "assigned", "closed"])
                },
                "context": {
                    "environment": "test"
                },
            }
        )

    return events
