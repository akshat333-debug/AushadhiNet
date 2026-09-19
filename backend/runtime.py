"""Runtime wiring shared by both modes: inbound-message routing, the
contacts registry, risk helpers and draft proposals. `start()` is local
mode only: it seeds the pilot district (facilities, dev contact numbers,
latest stock from the sealed synthetic ledger) and subscribes the worker
to the in-process queue. In cloud mode Firestore holds that state and
Pub/Sub pushes each message to backend/api/pubsub_push.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd

from backend.domain import Confidence, ConfidenceSource, Grain, RecordStatus, StockRecord
from backend.providers import factory

log = logging.getLogger(__name__)
PILOT_DISTRICT = "mh/nashik"
_CONFIRM_WORDS = {"YES", "CONFIRM", "Y", "हो", "हां"}
_HELP = "Send stock as '<medicine> <quantity>', one per line, e.g. 'ORS 50'. Or send a photo of the register."


@lru_cache(maxsize=1)
def forecast_panel() -> pd.DataFrame:
    from ml.data.panel import build
    return build(Grain.FACILITY_WEEK)


@lru_cache(maxsize=1)
def weekly_demand() -> dict[tuple[str, str], float]:
    """Mean units dispensed per week over the last 4 ledger weeks, per (facility, drug)."""
    panel = forecast_panel()
    recent = panel[panel["week"] > panel["week"].max() - pd.Timedelta(weeks=4)]
    return recent.groupby(["facility_id", "drug_id"])["dispensed"].mean().to_dict()


def below_cover(record) -> bool:
    """At risk = less than one week of recent demand on hand, for items that
    actually move (>= 1 unit/week); a never-used item at zero stock is not a shortage."""
    try:
        demand = weekly_demand().get((record.facility_id, record.drug_id), 0.0)
    except FileNotFoundError:
        return record.on_hand == 0
    return demand >= 1.0 and record.on_hand < demand


def phone_for_facility(facility_id: str) -> str:
    # ponytail: dev numbering derived from the ID; a real deployment keeps a contacts registry in Firestore.
    digits = "".join(c for c in facility_id if c.isdigit())
    return f"whatsapp:+9198{digits[-8:].zfill(8)}"


def facility_for_phone(phone: str) -> str | None:
    contact = factory.get("store_live").get("contacts", phone)
    return contact.facility_id if contact else None


def seed_contacts() -> int:
    from backend.domain import Contact
    from ml.data.facilities import facility_index
    live = factory.get("store_live")
    pilot = [f for f in facility_index().values() if f.district_id == PILOT_DISTRICT]
    for f in pilot:
        phone = phone_for_facility(f.facility_id)
        live.put("contacts", phone, Contact(phone=phone, facility_id=f.facility_id))
    return len(pilot)


def seed() -> int:
    """Loads the latest ledger week for the pilot district as confirmed stock. Returns records written."""
    live = factory.get("store_live")
    try:
        panel = forecast_panel()
    except FileNotFoundError:
        log.warning("data/synthetic missing: run `uv run python -m eval.seal_generator`; starting with no stock")
        return 0
    latest = panel[panel["week"] == panel["week"].max()]
    now = datetime.now(timezone.utc)
    confidence = Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.IMPORT)
    for row in latest.itertuples():
        record = StockRecord(
            record_id=f"seed-{row.facility_id}-{row.drug_id}", facility_id=row.facility_id, drug_id=row.drug_id,
            reported_at=now, as_of_date=pd.Timestamp(row.week).date(), on_hand=int(row.on_hand_close),
            dispensed=int(row.dispensed), status=RecordStatus.CONFIRMED, confidence=confidence.model_copy(),
            reporter_phone_hash="seed", raw_message_id=f"seed-{pd.Timestamp(row.week).date()}",
        )
        live.put("stock_records", record.record_id, record)
    return len(latest)


def latest_records() -> dict[tuple[str, str], StockRecord]:
    """Newest confirmed stock record per (facility, drug)."""
    newest: dict[tuple[str, str], StockRecord] = {}
    for r in factory.get("store_live").query("stock_records", {"status": RecordStatus.CONFIRMED}):
        key = (r.facility_id, r.drug_id)
        if key not in newest or r.reported_at > newest[key].reported_at:
            newest[key] = r
    return newest


def latest_stock(facility_ids: set[str]) -> dict[tuple[str, str], float]:
    return {k: float(v.on_hand) for k, v in latest_records().items() if k[0] in facility_ids}


def propose_for_district(district_id: str) -> list:
    from ml.data.facilities import facility_index
    from ml.optimize.service import propose
    facilities = [f for f in facility_index().values() if f.district_id == district_id]
    panel = forecast_panel()
    ids = {f.facility_id for f in facilities}
    drug_ids = sorted(panel.loc[panel["facility_id"].isin(ids), "drug_id"].unique())
    if not drug_ids:
        return []
    return propose(facilities, drug_ids, {}, latest_stock(ids), panel=panel)


def replace_drafts(district_id: str, drafts: list) -> list:
    """Stores a fresh solver run as the district's drafts; earlier unactioned
    solver drafts for the district are marked expired so proposals don't pile up."""
    from backend.domain import OrderStatus
    from ml.data.facilities import facility_index
    index = facility_index()
    live = factory.get("store_live")
    for old in live.query("orders", {"status": OrderStatus.DRAFT}):
        if getattr(index.get(old.from_facility_id), "district_id", None) == district_id:
            live.put("orders", old.order_id, old.model_copy(update={"status": OrderStatus.EXPIRED}))
    for order in drafts:
        assert order.status == OrderStatus.DRAFT
        live.put("orders", order.order_id, order)
    return drafts


def handle_inbound(payload: dict) -> None:
    from backend.api.worker import handle_stock_message
    from backend.ingest.cards import apply_reply
    messaging = factory.get("messaging")
    sender = payload["from"]
    facility_id = facility_for_phone(sender)
    if facility_id is None:
        messaging.send_text(sender, "This number is not registered to a facility.")
        return

    body = (payload.get("body") or "").strip()
    if not payload.get("num_media") and body.upper() in _CONFIRM_WORDS:
        live = factory.get("store_live")
        pending = live.query("stock_records", {"facility_id": facility_id, "status": RecordStatus.PENDING})
        for record in pending:
            confirmed = apply_reply(record, {})
            live.put("stock_records", confirmed.record_id, confirmed)
            factory.get("store_history").insert("stock_records", [confirmed.model_dump(mode="json")])
        messaging.send_text(sender, f"Confirmed {len(pending)} record(s)." if pending else "Nothing waiting for confirmation.")
        return

    decision = handle_stock_message(payload, facility_id)
    if decision.confirmed:
        lines = ", ".join(f"{r.drug_id} {r.on_hand}" for r in decision.confirmed)
        messaging.send_text(sender, f"Recorded for {facility_id}: {lines}.")
    elif decision.card is None:
        messaging.send_text(sender, f"Could not read that. {_HELP}")


def start() -> None:
    from ml.data.facilities import facility_index
    facility_index()  # national directory load takes seconds; pay it at startup, not on the first request
    seed_contacts()
    factory.get("queue").subscribe("ingest.raw_message", handle_inbound)
    log.info("seeded %d stock records for %s", seed(), PILOT_DISTRICT)


if __name__ == "__main__":
    # One-off cloud seeding: `AUSHADHI_MODE=cloud python -m backend.runtime seed` loads the pilot
    # district's contacts and latest ledger stock into Firestore.
    import sys
    if sys.argv[1:] != ["seed"]:
        raise SystemExit("usage: python -m backend.runtime seed")
    print(f"contacts: {seed_contacts()}, stock records: {seed()}")
