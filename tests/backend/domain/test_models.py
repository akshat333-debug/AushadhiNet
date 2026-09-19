"""DoD test for backend/domain/ (step 5)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from backend.domain import (
    BatchLine, BedCensus, CheckIn, Confidence, ConfidenceSource,
    Drug, Facility, FacilityType, Forecast, Grain, OrderKind, OrderStatus,
    RecordStatus, StaffRole, StockRecord, TransferOrder,
)


def _conf(overall=0.9, **fields) -> Confidence:
    return Confidence(field_confidence=fields, overall=overall, source=ConfidenceSource.GEMINI)


# --- Confidence ---

def test_confidence_low_fields():
    c = _conf(0.9, drug=0.95, quantity=0.6, expiry=0.4)
    assert c.low_fields(0.85) == ["quantity", "expiry"]


# --- Facility ---

def test_facility_valid():
    f = Facility(
        facility_id="MH-0000001", name="PHC Trimbak", state_code="MH",
        district_id="mh/nashik", facility_type=FacilityType.PHC,
        lat=19.93, lon=73.53, beds_sanctioned=6,
    )
    assert f.facility_type == FacilityType.PHC


@pytest.mark.parametrize("lat,lon", [(91.0, 0.0), (0.0, 181.0), (-91.0, 0.0)])
def test_facility_rejects_bad_coordinates(lat, lon):
    with pytest.raises(ValidationError):
        Facility(
            facility_id="x", name="x", state_code="MH", district_id="mh/nashik",
            facility_type=FacilityType.PHC, lat=lat, lon=lon,
        )


def test_facility_rejects_negative_beds():
    with pytest.raises(ValidationError):
        Facility(
            facility_id="x", name="x", state_code="MH", district_id="mh/nashik",
            facility_type=FacilityType.PHC, lat=0, lon=0, beds_sanctioned=-1,
        )


# --- Drug ---

def test_drug_rejects_bad_nlem_level():
    with pytest.raises(ValidationError):
        Drug(drug_id="ors", name="ORS", unit="sachet", nlem_level="X")


# --- StockRecord ---

def _stock(**overrides) -> StockRecord:
    base = dict(
        record_id="r1", facility_id="MH-0000001", drug_id="ors",
        reported_at=datetime(2019, 9, 1, tzinfo=timezone.utc),
        as_of_date=date(2019, 9, 1), on_hand=10,
        confidence=_conf(0.9, on_hand=0.9),
        reporter_phone_hash="h1", raw_message_id="m1",
    )
    base.update(overrides)
    return StockRecord(**base)


def test_stock_record_rejects_negative_on_hand():
    with pytest.raises(ValidationError):
        _stock(on_hand=-1)


def test_stock_record_forces_low_confidence_when_expiry_before_report():
    rec = _stock(
        expiry=date(2019, 8, 1),
        confidence=_conf(0.9, on_hand=0.9, expiry=0.95),
    )
    assert rec.confidence.field_confidence["expiry"] <= 0.0


def test_stock_record_default_status_pending():
    assert _stock().status == RecordStatus.PENDING


# --- BedCensus ---

def test_bed_census_rejects_occupied_over_total():
    with pytest.raises(ValidationError):
        BedCensus(
            record_id="b1", facility_id="MH-0000001", as_of_date=date(2019, 9, 1),
            beds_total=5, beds_occupied=6, confidence=_conf(), raw_message_id="m1",
        )


def test_bed_census_accepts_valid():
    b = BedCensus(
        record_id="b1", facility_id="MH-0000001", as_of_date=date(2019, 9, 1),
        beds_total=5, beds_occupied=5, confidence=_conf(), raw_message_id="m1",
    )
    assert b.beds_occupied == 5


# --- CheckIn ---

def test_checkin_round_trip():
    c = CheckIn(
        record_id="c1", facility_id="MH-0000001", staff_id_hash="h1",
        role=StaffRole.ANM, at=datetime(2019, 9, 1, tzinfo=timezone.utc),
        lat=19.9, lon=73.5, distance_m=50.0, geofence_ok=True, raw_message_id="m1",
    )
    again = CheckIn.model_validate_json(c.model_dump_json())
    assert again == c


# --- Forecast ---

def _forecast(**overrides) -> Forecast:
    base = dict(
        forecast_id="f1", grain=Grain.DISTRICT_MONTH, entity_id="mh/nashik",
        drug_id="ors", origin_date=date(2019, 9, 1), horizon=1,
        p50=100.0, p10=80.0, p90=120.0, stockout_prob=0.2,
        model="lgbm", model_version="0.1", features_hash="abc",
    )
    base.update(overrides)
    return Forecast(**base)


def test_forecast_rejects_bad_probability():
    with pytest.raises(ValidationError):
        _forecast(stockout_prob=1.5)


def test_forecast_rejects_unordered_quantiles():
    with pytest.raises(ValidationError):
        _forecast(p10=150.0, p50=100.0, p90=120.0)


def test_forecast_rejects_zero_horizon():
    with pytest.raises(ValidationError):
        _forecast(horizon=0)


# --- TransferOrder ---

def _order(**overrides) -> TransferOrder:
    base = dict(
        order_id="o1", kind=OrderKind.DRUG_TRANSFER,
        from_facility_id="MH-0000001", to_facility_id="MH-0000002",
        drug_id="ors", quantity=10, batches=[BatchLine(batch_no="B1", quantity=10)],
        drive_minutes=25.0, rationale="stock-out risk", created_at=datetime(2019, 9, 1, tzinfo=timezone.utc),
        created_by="solver",
    )
    base.update(overrides)
    return TransferOrder(**base)


def test_order_rejects_same_facility():
    with pytest.raises(ValidationError):
        _order(to_facility_id="MH-0000001")


def test_order_rejects_mismatched_batch_sum():
    with pytest.raises(ValidationError):
        _order(quantity=10, batches=[BatchLine(batch_no="B1", quantity=5)])


def test_order_rejects_signature_on_draft():
    with pytest.raises(ValidationError):
        _order(signature="sig", status=OrderStatus.DRAFT)


def test_order_allows_signature_when_approved():
    o = _order(signature="sig", status=OrderStatus.APPROVED)
    assert o.signature == "sig"


def test_deputation_order_does_not_require_drug_fields():
    o = _order(
        kind=OrderKind.DEPUTATION, drug_id=None, quantity=None, batches=[],
        staff_id_hash="h1",
    )
    assert o.kind == OrderKind.DEPUTATION


def test_order_rejects_bad_created_by():
    with pytest.raises(ValidationError):
        _order(created_by="nobody")


# --- round-trip for every model (one instance each) ---

@pytest.mark.parametrize("instance", [
    _conf(0.9, x=0.5),
    Facility(facility_id="x", name="x", state_code="MH", district_id="mh/nashik",
              facility_type=FacilityType.PHC, lat=0, lon=0),
    Drug(drug_id="ors", name="ORS", unit="sachet", nlem_level="P"),
    _stock(),
    BedCensus(record_id="b1", facility_id="MH-0000001", as_of_date=date(2019, 9, 1),
              beds_total=5, beds_occupied=3, confidence=_conf(), raw_message_id="m1"),
    CheckIn(record_id="c1", facility_id="MH-0000001", staff_id_hash="h1",
            role=StaffRole.ANM, at=datetime(2019, 9, 1, tzinfo=timezone.utc),
            lat=19.9, lon=73.5, distance_m=50.0, geofence_ok=True, raw_message_id="m1"),
    _forecast(),
    _order(),
])
def test_round_trip_lossless(instance):
    cls = type(instance)
    again = cls.model_validate_json(instance.model_dump_json())
    assert again == instance
