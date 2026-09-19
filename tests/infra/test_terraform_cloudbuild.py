"""DoD test for infra/terraform/ + cloudbuild.yaml (step 45).

HONEST NOTE: `terraform validate` is NOT run here -- the Terraform CLI is
not installed in this sandbox (see infra/terraform/state-module/main.tf's
header comment). This test does a structural/syntactic check (balanced
blocks, required variables declared, no hardcoded secrets) as the closest
available substitute; it does not replace running the real CLI once a GCP
project exists, per AC11's explicit deferral until credits arrive.
"""
from __future__ import annotations

import pathlib
import re

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
