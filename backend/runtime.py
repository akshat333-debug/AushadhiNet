"""Runtime wiring shared by both modes: inbound-message routing, the
contacts registry, risk helpers and draft proposals. `start()` is local
mode only: it seeds the pilot district (facilities, dev contact numbers,
latest stock from the sealed synthetic ledger) and subscribes the worker
to the in-process queue. In cloud mode Firestore holds that state and
Pub/Sub pushes each message to backend/api/pubsub_push.py.
"""
from __future__ import annotations

import logging
import pathlib
import threading
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd

from backend.domain import Confidence, ConfidenceSource, Grain, RecordStatus, StockRecord
from backend.providers import factory

log = logging.getLogger(__name__)
PILOT_DISTRICT = "mh/nashik"
# Every order status change (approve, reject, expire) re-checks and writes under this lock, so a
# proposal can't expire an order that was approved a moment ago. shortcut: a process lock, correct
# while Cloud Run runs one backend instance; use a Firestore transaction if it scales out.
ORDER_LOCK = threading.Lock()
SYNTHETIC_STOCK = pathlib.Path(__file__).resolve().parents[1] / "data" / "synthetic" / "stock.parquet"


@lru_cache(maxsize=1)
def forecast_panel() -> pd.DataFrame:
    """Recent ledger weeks only (backend.config.serving_weeks): forecasts read the last
    8 weeks and seeding the last one, so the API never needs the full 1.8M-row panel."""
    from backend.config import get_settings
    from ml.data.panel import build
    recent = SYNTHETIC_STOCK.with_name("stock_recent.parquet")
    if recent.exists():
        panel = pd.read_parquet(recent)  # written by eval/seal_generator.py
    else:
        last_week = pd.read_parquet(SYNTHETIC_STOCK, columns=["week"])["week"].max()
        since = (last_week - pd.Timedelta(weeks=get_settings().serving_weeks)).date()
        panel = build(Grain.FACILITY_WEEK, since=since)
    for col in ("facility_id", "drug_id"):
        panel[col] = panel[col].astype("category")
    return panel


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


def reply_lang(payload: dict) -> str:
    """Message's own language if the channel sent one, else the contact's preference."""
    from backend.i18n import norm_lang
    if payload.get("lang"):
        return norm_lang(payload["lang"])
    contact = factory.get("store_live").get("contacts", payload["from"])
    return norm_lang(contact.lang if contact else None)


def seed_contacts() -> int:
    from backend.domain import Contact
    from ml.data.facilities import served_facility_index as facility_index
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
    records = {}
    for row in latest.itertuples():
        record = StockRecord(
            record_id=f"seed-{row.facility_id}-{row.drug_id}", facility_id=row.facility_id, drug_id=row.drug_id,
            reported_at=now, as_of_date=pd.Timestamp(row.week).date(), on_hand=int(row.on_hand_close),
            dispensed=int(row.dispensed), status=RecordStatus.CONFIRMED, confidence=confidence.model_copy(),
            reporter_phone_hash="seed", raw_message_id=f"seed-{pd.Timestamp(row.week).date()}",
        )
        records[record.record_id] = record
    live.put_many("stock_records", records)
    global _latest
    _latest = None
    return len(latest)


# ponytail: in-process index, correct while the backend runs one instance (Cloud Run max 1);
# more instances would need a Firestore snapshot listener instead.
_latest: tuple[object, dict[tuple[str, str], StockRecord]] | None = None


def latest_records() -> dict[tuple[str, str], StockRecord]:
    """Newest confirmed stock record per (facility, drug). Read from the store once (a full
    Firestore read of the district takes ~8 s), then kept current by note_confirmed()."""
    global _latest
    live = factory.get("store_live")
    if _latest is None or _latest[0] is not live:
        newest: dict[tuple[str, str], StockRecord] = {}
        for r in live.query("stock_records", {"status": RecordStatus.CONFIRMED}):
            note_confirmed(r, newest)
        _latest = (live, newest)
    # A copy: reports update the index from other threads, and adding a key while a caller loops
    # over it raises "dictionary changed size during iteration". dict() copies atomically.
    return dict(_latest[1])


def note_confirmed(record: StockRecord, index: dict | None = None) -> None:
    """Every write of a confirmed record goes through here so latest_records() stays current."""
    if index is None:
        if _latest is None:
            return
        index = _latest[1]
    key = (record.facility_id, record.drug_id)
    if key not in index or record.reported_at > index[key].reported_at:
        index[key] = record


def latest_stock(facility_ids: set[str]) -> dict[tuple[str, str], float]:
    return {k: float(v.on_hand) for k, v in latest_records().items() if k[0] in facility_ids}


def propose_for_district(district_id: str) -> list:
    from ml.data.facilities import served_facility_index as facility_index
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
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()
    live = factory.get("store_live")
    assert all(order.status == OrderStatus.DRAFT for order in drafts)
    with ORDER_LOCK:
        expired = {old.order_id: old.model_copy(update={"status": OrderStatus.EXPIRED})
                   for old in live.query("orders", {"status": OrderStatus.DRAFT})
                   if getattr(index.get(old.from_facility_id), "district_id", None) == district_id}
        live.put_many("orders", expired)
    live.put_many("orders", {order.order_id: order for order in drafts})
    return drafts


def handle_inbound(payload: dict) -> None:
    from backend.api.worker import handle_bed_census, handle_stock_message
    from backend.capacity import parse_beds
    from backend.i18n import CONFIRM_WORDS, drug_name, msg
    from backend.ingest.cards import apply_reply
    messaging = factory.get("messaging")
    sender = payload["from"]
    lang = reply_lang(payload)
    payload = {**payload, "lang": lang}
    facility_id = facility_for_phone(sender)
    if facility_id is None:
        messaging.send_text(sender, msg(lang, "not_registered"))
        return

    body = (payload.get("body") or "").strip()
    if payload.get("latitude") is not None:
        _check_in(payload, facility_id, body, lang)
        return
    beds = None if payload.get("num_media") else parse_beds(body)
    if beds is not None:
        try:
            handle_bed_census(payload, facility_id, beds_total=beds[1], beds_occupied=beds[0])
        except ValueError:  # more occupied than total
            messaging.send_text(sender, msg(lang, "beds_invalid"))
            return
        messaging.send_text(sender, msg(lang, "beds_recorded", facility=facility_id, occupied=beds[0], total=beds[1]))
        return
    if not payload.get("num_media") and body.upper() in CONFIRM_WORDS:
        live = factory.get("store_live")
        pending = live.query("stock_records", {"facility_id": facility_id, "status": RecordStatus.PENDING})
        for record in pending:
            confirmed = apply_reply(record, {})
            live.put("stock_records", confirmed.record_id, confirmed)
            note_confirmed(confirmed)
            factory.get("store_history").insert("stock_records", [confirmed.model_dump(mode="json")])
        messaging.send_text(sender, msg(lang, "confirmed_n", n=len(pending)) if pending else msg(lang, "nothing_pending"))
        return

    decision = handle_stock_message(payload, facility_id)
    if decision.confirmed:
        items = ", ".join(f"{drug_name(r.drug_id, lang)} {r.on_hand}" for r in decision.confirmed)
        messaging.send_text(sender, msg(lang, "recorded", facility=facility_id, items=items))
    elif decision.card is None:
        messaging.send_text(sender, msg(lang, "unreadable"))


def _check_in(payload: dict, facility_id: str, body: str, lang: str) -> None:
    """A shared WhatsApp location is a staff check-in, checked against the facility's geofence."""
    from backend.api.worker import handle_checkin
    from backend.capacity import IST, role_from
    from backend.i18n import msg
    from ml.data.facilities import served_facility_index
    facility = served_facility_index()[facility_id]
    record = handle_checkin(payload, facility_id, payload["reporter_phone_hash"], role_from(body),
                            float(payload["latitude"]), float(payload["longitude"]), facility.lat, facility.lon)
    text = (msg(lang, "checkin_ok", facility=facility_id, time=record.at.astimezone(IST).strftime("%H:%M")) if record.geofence_ok
            else msg(lang, "checkin_far", facility=facility_id, km=f"{record.distance_m / 1000:.1f}"))
    factory.get("messaging").send_text(payload["from"], text)


def warm() -> None:
    from backend.ingest.nlem import match
    from ml.data.facilities import served_facility_index as facility_index
    facility_index()  # directory load takes seconds; pay it at startup, not on the first request
    match("ors")  # builds the drug-name index (PDF parse + embeddings): minutes on a small CPU
    weekly_demand()
    latest_records()  # one full read of the stock store (~8 s on Firestore), then served from memory
    from ml.data.facilities import coverage
    coverage()


def start() -> None:
    warm()
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
