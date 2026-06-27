"""Transactions tasks: paginated GET, POST, DELETE."""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from locust import task, TaskSet

from tasks.auth import auth_headers


def _sample_payload() -> dict:
    txn_date = date.today() - timedelta(days=random.randint(0, 30))
    return {
        "description": f"bench txn {uuid.uuid4().hex[:8]}",
        "amount_cents": random.choice([-2599, -1099, -499, 1500, 4200, -8750]),
        "transaction_date": txn_date.isoformat(),
        "merchant": random.choice(["Acme", "Globex", "Initech", "Soylent", "Umbrella"]),
        "tags": [],
    }


class TransactionTaskSet(TaskSet):
    @task(8)
    def list_transactions(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        page = random.randint(1, 5)
        self.client.get(
            "/api/transactions",
            params={"page": page, "page_size": 25},
            headers=auth_headers(token),
            name="GET /api/transactions",
        )

    @task(2)
    def create_transaction(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        with self.client.post(
            "/api/transactions",
            params={"notify": "false"},
            json=_sample_payload(),
            headers=auth_headers(token),
            name="POST /api/transactions",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                try:
                    txn_id = resp.json().get("id")
                except ValueError:
                    txn_id = None
                if txn_id:
                    self.user.created_transaction_ids.append(txn_id)
                resp.success()
            else:
                resp.failure(f"create status={resp.status_code}")

    @task(1)
    def delete_transaction(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        ids = getattr(self.user, "created_transaction_ids", None)
        if not ids:
            return
        txn_id = ids.pop()
        self.client.delete(
            f"/api/transactions/{txn_id}",
            headers=auth_headers(token),
            name="DELETE /api/transactions/{id}",
        )
