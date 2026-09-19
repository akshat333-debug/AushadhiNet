"""DoD test for backend/action/alerts.py (step 34, AC8)."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.domain import BatchLine, Facility, FacilityType, OrderKind, TransferOrder
from backend.providers import factory

from backend.action.alerts import send_transfer_alerts


def _facility(fid, name):
    return Facility(facility_id=fid, name=name, state_code="MH", district_id="mh/nashik",
                      facility_type=FacilityType.PHC, lat=20.0, lon=73.8)


def _order():
    return TransferOrder(
        order_id="o1", kind=OrderKind.DRUG_TRANSFER, from_facility_id="F1", to_facility_id="F2",
        drug_id="ors", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="stock-out risk", created_at=datetime.now(timezone.utc), created_by="solver",
    )


def test_alerts_sent_to_both_facilities_in_local_language():
    order = _order()
    f1, f2 = _facility("F1", "PHC Alpha"), _facility("F2", "PHC Beta")
    send_transfer_alerts(order, f1, f2, "+911111111111", "+912222222222", lang="mr", drug_name="ORS")

    messaging = factory.get("messaging")
    recipients = {m.to for m in messaging.sent}
    assert recipients == {"+911111111111", "+912222222222"}
    text_messages = [m for m in messaging.sent if m.kind == "text"]
    assert len(text_messages) == 2
    assert all(m.body.startswith("[mr]") for m in text_messages)  # local translate tag


def test_alerts_include_voice_media():
    order = _order()
    f1, f2 = _facility("F1", "PHC Alpha"), _facility("F2", "PHC Beta")
    send_transfer_alerts(order, f1, f2, "+911111111111", "+912222222222")
    messaging = factory.get("messaging")
    media_messages = [m for m in messaging.sent if m.kind == "media"]
    assert len(media_messages) == 2
    assert all(m.body.startswith("data:audio/") for m in media_messages)


def test_route_plan_text_mentions_both_facilities():
    from backend.action.alerts import route_plan_text
    f1, f2 = _facility("F1", "PHC Alpha"), _facility("F2", "PHC Beta")
    text = route_plan_text(_order(), f1, f2)
    assert "PHC Alpha" in text and "PHC Beta" in text and "min" in text
