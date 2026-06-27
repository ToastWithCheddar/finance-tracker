"""Notifications router (mounted at `/api/notifications`).

Coverage:
- GET    /api/notifications/             list (with unread_only filter)
- GET    /api/notifications/stats        unread/total counts
- PATCH  /api/notifications/{id}         mark single as read
- POST   /api/notifications/mark-all-read

We seed the DB with `Notification` rows directly (no public POST endpoint —
notifications are created server-side via `NotificationService`).
"""

from __future__ import annotations

import pytest

from factories import UserFactory
from helpers.auth_client import make_authenticated_client


def _seed_notification(db_session, user, *, is_read=False, title="Test"):
    from app.models.notification import Notification, NotificationType

    n = Notification(
        user_id=user.id,
        type=NotificationType.INFO,
        title=title,
        message="Test message body",
        is_read=is_read,
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)
    return n


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    client = make_authenticated_client(app_client, user)
    return client, user, db_session


@pytest.mark.integration
def test_notifications_list_and_stats(authed):
    client, user, db = authed
    _seed_notification(db, user, title="Unread one")
    _seed_notification(db, user, title="Read one", is_read=True)

    r = client.get("/api/notifications/")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 2
    assert body["unread_count"] >= 1

    r = client.get("/api/notifications/", params={"unread_only": "true"})
    assert r.status_code == 200, r.text
    items = r.json()["notifications"]
    assert all(item["is_read"] is False for item in items)

    r = client.get("/api/notifications/stats")
    assert r.status_code == 200, r.text


@pytest.mark.integration
def test_notification_mark_single_read(authed):
    client, user, db = authed
    n = _seed_notification(db, user, title="Mark me")

    r = client.patch(f"/api/notifications/{n.id}", json={"is_read": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_read"] is True


@pytest.mark.integration
def test_notification_mark_all_read(authed):
    client, user, db = authed
    _seed_notification(db, user, title="A")
    _seed_notification(db, user, title="B")
    _seed_notification(db, user, title="C")

    r = client.post("/api/notifications/mark-all-read")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["updated_count"] >= 3

    # Subsequent unread query should return zero rows.
    r = client.get("/api/notifications/", params={"unread_only": "true"})
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0
