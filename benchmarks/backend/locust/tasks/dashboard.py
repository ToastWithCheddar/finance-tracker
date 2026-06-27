"""Dashboard tasks. Targets BE-PERF-005 (sequential count() queries)."""
from __future__ import annotations

from locust import task, TaskSet

from tasks.auth import auth_headers


class DashboardTaskSet(TaskSet):
    @task(5)
    def summary(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        self.client.get(
            "/api/dashboard/summary",
            headers=auth_headers(token),
            name="GET /api/dashboard/summary",
        )

    @task(2)
    def category_breakdown(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        self.client.get(
            "/api/dashboard/category-breakdown",
            headers=auth_headers(token),
            name="GET /api/dashboard/category-breakdown",
        )

    @task(2)
    def net_worth_trend(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        self.client.get(
            "/api/dashboard/net-worth-trend",
            params={"period": "90d"},
            headers=auth_headers(token),
            name="GET /api/dashboard/net-worth-trend",
        )
