"""infra/terraform/ + cloudbuild.yaml: structure, `terraform validate` when
the CLI is installed, and drift between Terraform, Cloud Build and the code."""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

INFRA_DIR = pathlib.Path(__file__).resolve().parents[2] / "infra"


def test_terraform_module_braces_are_balanced():
    text = (INFRA_DIR / "terraform" / "state-module" / "main.tf").read_text()
    assert text.count("{") == text.count("}")


def test_terraform_module_declares_required_variables():
    text = (INFRA_DIR / "terraform" / "state-module" / "main.tf").read_text()
    for var in ("project_id", "state_code", "region"):
        assert f'variable "{var}"' in text


def test_terraform_module_has_no_hardcoded_secrets():
    """Resource/dataset NAMES (e.g. "aushadhinet-order-signing") are fine
    and expected in HCL; what must never appear is a value assigned to a
    credential-shaped field."""
    text = (INFRA_DIR / "terraform" / "state-module" / "main.tf").read_text()
    assert "REPLACE_ME" not in text  # that placeholder belongs only in the .tfvars.example
    suspicious = re.findall(
        r'(?i)\b(api_key|secret|password|auth_token|private_key)\s*=\s*"[^"]{8,}"', text
    )
    assert suspicious == [], f"credential-shaped hardcoded value(s) in main.tf: {suspicious}"


def test_tfvars_example_uses_placeholder_not_a_real_project():
    text = (INFRA_DIR / "terraform" / "state-module" / "variables.tfvars.example").read_text()
    assert "REPLACE_ME" in text


def test_cloudbuild_yaml_is_valid_and_has_expected_steps():
    config = yaml.safe_load((INFRA_DIR / "cloudbuild.yaml").read_text())
    assert "steps" in config and len(config["steps"]) >= 2
    assert any("docker" in step.get("name", "") for step in config["steps"])
    assert any("run" in step.get("args", []) for step in config["steps"])


def test_cloudbuild_deploys_in_cloud_mode_not_local():
    config = yaml.safe_load((INFRA_DIR / "cloudbuild.yaml").read_text())
    deploy_step = next(s for s in config["steps"] if "run" in s.get("args", []))
    assert any("AUSHADHI_MODE=cloud" in arg for arg in deploy_step["args"])


MODULE = INFRA_DIR / "terraform" / "state-module"


def test_terraform_validate_passes():
    if shutil.which("terraform") is None:
        pytest.skip("terraform CLI not installed")
    subprocess.run(["terraform", "init", "-backend=false", "-input=false"], cwd=MODULE, check=True, capture_output=True)
    result = subprocess.run(["terraform", "validate", "-no-color"], cwd=MODULE, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_bigquery_schemas_match_the_models_the_code_inserts():
    from backend.domain import BedCensus, CheckIn, StockRecord
    text = (MODULE / "main.tf").read_text()
    for table, model in (("stock_records", StockRecord), ("bed_census", BedCensus), ("checkins", CheckIn)):
        block = re.search(rf"{table} = \[(.*?)\n    \]", text, re.S).group(1)
        columns = re.findall(r'\["([a-z_]+)", "[A-Z0-9]+", "(?:REQUIRED|NULLABLE)"\]', block)
        assert columns == list(model.model_fields), f"{table} schema drifted from {model.__name__}"


def test_pubsub_names_match_the_queue_provider():
    text = (MODULE / "main.tf").read_text()
    assert 'name                 = "ingest.raw_message-sub"' in text
    assert 'name       = "ingest.raw_message"' in text


def test_cloudbuild_references_resources_terraform_creates():
    text = (MODULE / "main.tf").read_text()
    build = (INFRA_DIR / "cloudbuild.yaml").read_text()
    for name in ("aushadhinet-backend@", "pubsub-push@", "aushadhinet-order-signing", "transfer-order-signer",
                 "twilio-auth-token", "gemini-api-key"):
        assert name in build, f"{name} missing from cloudbuild.yaml"
    for name in ('account_id   = "aushadhinet-backend"', 'account_id   = "pubsub-push"', '"twilio-auth-token"', '"gemini-api-key"',
                 'repository_id = "aushadhinet"'):
        assert name in text, f"{name} missing from main.tf"
    assert "gcr.io/$PROJECT_ID" not in build  # Container Registry is deprecated; images go to Artifact Registry
