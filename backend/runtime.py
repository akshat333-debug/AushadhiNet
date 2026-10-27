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
import re
import threading
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
from pydantic import BaseModel

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
    if get_settings().mode == "local" or get_settings().demo_mode:
        panel = pd.concat([panel, neighbour_demo_panel(panel)], ignore_index=True)
    for col in ("facility_id", "drug_id"):
        panel[col] = panel[col].astype("category")
    return panel


NEIGHBOUR_DISTRICT = "mh/dhule"
NEIGHBOUR_FACILITIES = 15
NEIGHBOUR_REPORTER = "demo-neighbour"  # marks the generated Dhule stock wherever it is stored


def neighbour_demo_facilities() -> list:
    """The Dhule PHCs and CHCs nearest Nashik: a second district with stock, so a State officer
    can see surplus cross the district line live. Demo data only: never in any evaluation."""
    from backend.domain import FacilityType
    from ml.data.facilities import served_facility_index
    index = served_facility_index().values()
    pilot = [(f.lat, f.lon) for f in index if f.district_id == PILOT_DISTRICT]
    near = lambda f: min((f.lat - a) ** 2 + (f.lon - b) ** 2 for a, b in pilot)
    candidates = [f for f in index if f.district_id == NEIGHBOUR_DISTRICT and f.facility_type in (FacilityType.PHC, FacilityType.CHC)]
    return sorted(candidates, key=near)[:NEIGHBOUR_FACILITIES]


def neighbour_demo_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Each demo Dhule facility mirrors the demand of its nearest Nashik facility (same weeks)."""
    from ml.data.facilities import served_facility_index
    index = served_facility_index()
    pilot = [f for f in index.values() if f.district_id == PILOT_DISTRICT and f.facility_id in set(panel["facility_id"].astype(str))]
    rows = []
    for f in neighbour_demo_facilities():
        twin = min(pilot, key=lambda p: (p.lat - f.lat) ** 2 + (p.lon - f.lon) ** 2)
        mirrored = panel[panel["facility_id"].astype(str) == twin.facility_id].copy()
        mirrored["facility_id"] = f.facility_id
        rows.append(mirrored)
    return pd.concat(rows, ignore_index=True) if rows else panel.iloc[:0]


def seed_neighbour() -> int:
    """Demo stock for the Dhule facilities: four weeks of their demand, so they hold surplus beyond
    the two weeks a donor keeps. Writes only these facilities; Nashik's live stock is untouched."""
    from backend.domain import Contact
    live = factory.get("store_live")
    panel = forecast_panel()
    ids = {f.facility_id for f in neighbour_demo_facilities()}
    recent = panel[panel["facility_id"].astype(str).isin(ids)]
    recent = recent[recent["week"] > recent["week"].max() - pd.Timedelta(weeks=4)]
    now = datetime.now(timezone.utc)
    records = {}
    for (fid, drug), g in recent.groupby(["facility_id", "drug_id"], observed=True):
        rid = f"demo-{fid}-{drug}"
        records[rid] = StockRecord(
            record_id=rid, facility_id=str(fid), drug_id=str(drug), reported_at=now, as_of_date=now.date(),
            on_hand=int(round(4 * g["dispensed"].mean())), status=RecordStatus.CONFIRMED,
            confidence=Confidence(field_confidence={"on_hand": 1.0}, overall=1.0, source=ConfidenceSource.IMPORT),
            reporter_phone_hash=NEIGHBOUR_REPORTER, raw_message_id="demo-neighbour-seed")
    live.put_many("stock_records", records)
    for fid in ids:
        phone = phone_for_facility(fid)
        live.put("contacts", phone, Contact(phone=phone, facility_id=fid))
    global _latest
    _latest = None
    return len(records)


@lru_cache(maxsize=1)
def _ledger_demand() -> dict[tuple[str, str], float]:
    """Mean units dispensed per week over the last 4 ledger weeks, per (facility, drug)."""
    panel = forecast_panel()
    recent = panel[panel["week"] > panel["week"].max() - pd.Timedelta(weeks=4)]
    return recent.groupby(["facility_id", "drug_id"])["dispensed"].mean().to_dict()


_demand_cache: tuple[int, dict] | None = None


def weekly_demand() -> dict[tuple[str, str], float]:
    """Units used per week: a facility's own reported use where its counts show it, else the ledger.
    Rebuilt only when a new count changed some facility's use (callers ask once per record)."""
    global _demand_cache
    use = recent_use()
    if _demand_cache is None or _demand_cache[0] != _use_version:
        _demand_cache = (_use_version, {**_ledger_demand(), **{k: u for k, (u, _) in use.items()}})
    return _demand_cache[1]


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


def contact_phone(facility_id: str) -> str | None:
    """The facility's registered WhatsApp number (the contacts registry). Only local and demo
    mode fall back to the derived dev number; a real deployment alerts verified numbers only."""
    from backend.config import get_settings
    registered = factory.get("store_live").query("contacts", {"facility_id": facility_id})
    if registered:
        return sorted(c.phone for c in registered)[0]
    settings = get_settings()
    return phone_for_facility(facility_id) if settings.mode == "local" or settings.demo_mode else None


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
    global _latest, _use, _use_version, _moves
    live = factory.get("store_live")
    if _latest is None or _latest[0] is not live:
        newest: dict[tuple[str, str], StockRecord] = {}
        _use = None
        _dates.clear()
        _use_version += 1
        _moves = _moved_orders()  # one read, not one per report: startup must fit Cloud Run's probe
        try:
            for r in sorted(live.query("stock_records", {"status": RecordStatus.CONFIRMED}), key=lambda r: r.reported_at):
                note_confirmed(r, newest)
        finally:
            _moves = None
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
        _note_use(record)
        index[key] = record


SCENARIO_REPORTERS = {"seed", "demo-neighbour"}  # loaded ledger stock, not a nurse's count
_use = None  # ml.forecast.reported_use.UseEstimator, rebuilt with the stock index
_dates: dict[tuple[str, str], object] = {}
_use_version = 0


_moves: list | None = None  # moved transfer orders, read once while the index is rebuilt


def _moved_orders() -> list:
    from backend.domain import OrderKind, OrderStatus
    if _moves is not None:
        return _moves
    return [o for status in (OrderStatus.DISPATCHED, OrderStatus.RECEIVED)
            for o in factory.get("store_live").query("orders", {"status": status}) if o.kind == OrderKind.DRUG_TRANSFER]


def _net_in(facility_id: str, drug_id: str, since: datetime, until: datetime) -> float:
    """Units that arrived at a facility minus units that left it, in (since, until]."""
    net = 0.0
    for o in _moved_orders():
        if o.drug_id != drug_id:
            continue
        left, arrived = o.dispatched_at or o.received_at, o.received_at
        if o.to_facility_id == facility_id and arrived and since < arrived <= until:
            net += o.quantity
        if o.from_facility_id == facility_id and left and since < left <= until:
            net -= o.quantity
    return net


def _note_use(record: StockRecord) -> None:
    """Feeds a nurse's confirmed count to the shared use estimator (ml/forecast/reported_use.py),
    with the transfers that moved in and out since its anchor count. A loaded scenario count is
    not a count. shortcut: deliveries outside AushadhiNet (the state's monthly supply) are not
    known, so a count that rose across one gives no reading; add them when indents are recorded."""
    global _use, _use_version
    from ml.forecast.reported_use import UseEstimator
    if record.reporter_phone_hash in SCENARIO_REPORTERS:
        return
    _use = _use or UseEstimator()
    key = (record.facility_id, record.drug_id)
    day = record.reported_at.timestamp() / 86400
    anchor = _use.anchor(key)
    net = 0.0 if anchor is None else _net_in(*key, datetime.fromtimestamp(anchor[0] * 86400, timezone.utc), record.reported_at)
    if _use.observe(key, day, record.on_hand, net):
        _dates[key] = record.as_of_date
        _use_version += 1


def recent_use() -> dict[tuple[str, str], tuple[float, object]]:
    """(units per week, date of the count) per (facility, drug), from nurses' own counts."""
    latest_records()  # builds the index, and with it the observed use
    return {k: (r, _dates[k]) for k, r in (_use.rates.items() if _use else ())}


def latest_stock(facility_ids: set[str]) -> dict[tuple[str, str], float]:
    return {k: float(v.on_hand) for k, v in latest_records().items() if k[0] in facility_ids}


COMMITTED = ("approved", "dispatched", "received")
MIN_SHIPMENT = 10  # units: below this the live app drafts no transfer (the demo once proposed one glove)
MAX_SOURCES = 5    # donors per recipient and medicine. Nashik, 2026-10-26: 160 drafts (smallest 1 unit) became 77, keeping 68% of the units


def projected_stock(facility_ids: set[str], incoming: bool = True) -> dict[tuple[str, str], float]:
    """Stock per (facility, drug) after every approved transfer, from the latest reports.

    Units promised away stay reserved at the source until they leave (SENT <code>, or the
    receipt): a report the nurse sends before then still counts them, so they are taken off
    it. Once they have left, only reports older than their departure still count them.
    Units on their way are added at the destination for planning (`incoming=True`); for
    approval only what is physically there counts (`incoming=False`), so nothing is sent
    onward before it arrives. A report after arrival already includes them."""
    from backend.domain import OrderKind, OrderStatus
    latest = latest_records()
    stock = {k: float(v.on_hand) for k, v in latest.items() if k[0] in facility_ids}
    live = factory.get("store_live")

    def add(fid, drug, units):
        stock[(fid, drug)] = stock.get((fid, drug), 0.0) + units

    for status in COMMITTED:
        for o in live.query("orders", {"status": OrderStatus(status)}):
            if o.kind != OrderKind.DRUG_TRANSFER or o.approved_at is None:
                continue
            left = o.dispatched_at or o.received_at
            src = latest.get((o.from_facility_id, o.drug_id))
            if o.from_facility_id in facility_ids and (left is None or src is None or left > src.reported_at):
                add(o.from_facility_id, o.drug_id, -o.quantity)
            dst = latest.get((o.to_facility_id, o.drug_id))
            arrived_after_report = o.received_at is not None and (dst is None or o.received_at > dst.reported_at)
            if o.to_facility_id in facility_ids and (arrived_after_report or (incoming and o.received_at is None)):
                add(o.to_facility_id, o.drug_id, o.quantity)
    return stock


def in_scope(district_id: str, scope: str) -> bool:
    """A scope is a district ("mh/nashik") or a whole state ("mh")."""
    return district_id == scope or district_id.startswith(f"{scope}/")


def propose_for_district(scope: str) -> list:
    """Transfer drafts for a district, or for a whole state, where surplus in one district can
    cover a shortage in the next (cross-district orders then need a state officer to approve,
    backend/api/officer.py). Only facilities with stock history take part."""
    from ml.data.facilities import served_facility_index as facility_index
    from ml.optimize.service import propose
    panel = forecast_panel()
    use = recent_use()
    known = set(panel["facility_id"].unique()) | {f for f, _ in use}  # history, or its own reported use
    facilities = [f for f in facility_index().values() if in_scope(f.district_id, scope) and f.facility_id in known]
    ids = {f.facility_id for f in facilities}
    drug_ids = sorted(set(panel.loc[panel["facility_id"].isin(ids), "drug_id"].unique()) | {d for f, d in use if f in ids})
    if not drug_ids:
        return []
    from ml.optimize.constraints import SolverConfig
    return propose(facilities, drug_ids, {}, projected_stock(ids), cfg=SolverConfig(min_transfer_units=MIN_SHIPMENT, max_sources=MAX_SOURCES),
                   panel=panel, recent_use=use)


def replace_drafts(district_id: str, drafts: list) -> list:
    """Stores a fresh solver run as the scope's drafts; earlier unactioned solver drafts
    from the same district or state are marked expired so proposals don't pile up."""
    from backend.domain import OrderStatus
    from ml.data.facilities import served_facility_index as facility_index
    index = facility_index()
    live = factory.get("store_live")
    assert all(order.status == OrderStatus.DRAFT for order in drafts)
    with ORDER_LOCK:
        expired = {old.order_id: old.model_copy(update={"status": OrderStatus.EXPIRED})
                   for old in live.query("orders", {"status": OrderStatus.DRAFT})
                   if in_scope(getattr(index.get(old.from_facility_id), "district_id", ""), district_id)}
        live.put_many("orders", expired)
        live.put_many("orders", {order.order_id: order for order in drafts})  # inside the lock: two runs never both stay active
    return drafts


class _Seen(BaseModel):
    at: datetime


_inbound_lock = threading.Lock()
_in_flight: set[str] = set()


def handle_inbound(payload: dict) -> None:
    """Twilio and Pub/Sub both redeliver on timeouts, so each message id is handled once.
    shortcut: the in-flight set is per process, correct while the backend runs one instance."""
    sid = payload.get("message_sid")
    if not sid:
        return _handle_inbound(payload)
    live = factory.get("store_live")
    with _inbound_lock:
        if sid in _in_flight or live.get("inbound_seen", sid) is not None:
            log.info("duplicate delivery of %s ignored", sid)
            return
        _in_flight.add(sid)
    try:
        _handle_inbound(payload)
        live.put("inbound_seen", sid, _Seen(at=datetime.now(timezone.utc)))  # after success, so a failed attempt can be retried
    finally:
        with _inbound_lock:
            _in_flight.discard(sid)


def _handle_inbound(payload: dict) -> None:
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
    movement = None if payload.get("num_media") else re.fullmatch(r"\s*(RECEIVED|SENT)\s+([0-9a-f]{8})\s*", body, re.IGNORECASE)
    if movement:
        _movement(facility_id, movement.group(1).upper(), movement.group(2).lower(), sender, lang)
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
    if not payload.get("num_media") and body.upper().strip(" .!") in CONFIRM_WORDS | {"1"}:
        live = factory.get("store_live")
        pending = live.query("stock_records", {"facility_id": facility_id, "status": RecordStatus.PENDING})
        for record in pending:
            confirmed = apply_reply(record, {})
            live.put("stock_records", confirmed.record_id, confirmed)
            note_confirmed(confirmed)
            write_history(confirmed)
        messaging.send_text(sender, msg(lang, "confirmed_n", n=len(pending)) if pending else msg(lang, "nothing_pending"))
        return

    # A new report replaces any earlier one still waiting for YES, so YES (or a typed correction)
    # only ever applies to the card the nurse is looking at.
    # Only once the new message has been read: "hello" or "yes please" must not discard the card.
    live = factory.get("store_live")
    stale = live.query("stock_records", {"facility_id": facility_id, "status": RecordStatus.PENDING})
    decision = handle_stock_message(payload, facility_id)
    if decision.confirmed or decision.pending:
        new = decision.confirmed + decision.pending
        fresh, first = {r.record_id for r in new}, min(r.reported_at for r in new)
        for record in (r for r in stale if r.record_id not in fresh and r.reported_at < first):  # a late retry spares newer cards
            live.put("stock_records", record.record_id, record.model_copy(update={"status": RecordStatus.REJECTED}))
    if decision.confirmed:
        items = ", ".join(f"{drug_name(r.drug_id, lang)} {r.on_hand}" for r in decision.confirmed)
        messaging.send_text(sender, msg(lang, "recorded", facility=facility_id, items=items))
    elif decision.card is None and not decision.rejected:
        messaging.send_text(sender, msg(lang, "unreadable"))


def write_history(record: BaseModel, table: str = "stock_records") -> None:
    """BigQuery history is a copy of the live store; a failed insert must not make Pub/Sub
    redeliver the message and resend replies the nurse already got."""
    try:
        factory.get("store_history").insert(table, [record.model_dump(mode="json")])
    except Exception:  # noqa: BLE001
        log.exception("history insert failed for %s", record.record_id)


def _movement(facility_id: str, word: str, code: str, sender: str, lang: str) -> None:
    """SENT <code> from the source, RECEIVED <code> from the destination, by the code in the order alert."""
    from backend.api.officer import mark_dispatched, mark_received
    from backend.domain import OrderStatus
    from backend.i18n import msg
    live = factory.get("store_live")
    sent = word == "SENT"
    side, statuses = ("from_facility_id", (OrderStatus.APPROVED,)) if sent else ("to_facility_id", (OrderStatus.APPROVED, OrderStatus.DISPATCHED))
    match = [o for status in statuses for o in live.query("orders", {side: facility_id, "status": status}) if o.order_id.startswith(code)]
    key = "dispatch" if sent else "receipt"
    if len(match) != 1:
        factory.get("messaging").send_text(sender, msg(lang, f"{key}_unknown", code=code))
        return
    (mark_dispatched if sent else mark_received)(match[0])
    factory.get("messaging").send_text(sender, msg(lang, f"{key}_ok", code=code))


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
    log.info("seeded %d demo stock records for %s", seed_neighbour(), NEIGHBOUR_DISTRICT)


if __name__ == "__main__":
    # One-off cloud seeding: `AUSHADHI_MODE=cloud python -m backend.runtime seed` loads the pilot
    # district's contacts and latest ledger stock into Firestore.
    # `seed-neighbour` adds only the labelled Dhule demo stock (needs DEMO_MODE=true).
    import sys
    if sys.argv[1:] == ["seed"]:
        print(f"contacts: {seed_contacts()}, stock records: {seed()}")
    elif sys.argv[1:] == ["seed-neighbour"]:
        print(f"demo stock records for {NEIGHBOUR_DISTRICT}: {seed_neighbour()}")
    else:
        raise SystemExit("usage: python -m backend.runtime seed | seed-neighbour")
