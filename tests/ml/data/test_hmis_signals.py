"""DoD test for ml/data/hmis_m10_m11.py and ml/data/hmis_service.py (step 9)."""
from __future__ import annotations

from ml.data.facilities import load_facilities
from ml.data.hmis_m10_m11 import load_disease_signals
from ml.data.hmis_service import SERVICE_INDICATORS, load_service_indicators


def test_disease_district_keys_join_to_facility_directory():
    disease = load_disease_signals(states=["mah"])
    facility_districts = {f.district_id for f in load_facilities(state="Maharashtra")}
    disease_districts = set(disease["district_id"].unique())
    # every disease-signal district must be a real facility-directory district
    assert disease_districts <= facility_districts


def test_disease_signals_include_malaria_and_diarrhoea():
    disease = load_disease_signals(states=["mah"])
    indicators = set(disease["indicator"].unique())
    assert any("Malaria" in i for i in indicators)
    assert any("Diarrhoea" in i for i in indicators)


def test_service_indicators_present_for_nashik():
    svc = load_service_indicators(states=["mah"])
    nashik = svc[svc.district_id == "mh/nashik"]
    assert len(nashik) > 0
    for key in SERVICE_INDICATORS:
        assert nashik[key].notna().any()


def test_service_district_keys_join_to_facility_directory():
    svc = load_service_indicators(states=["mah"])
    facility_districts = {f.district_id for f in load_facilities(state="Maharashtra")}
    assert set(svc["district_id"].unique()) <= facility_districts
