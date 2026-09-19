"""TransferOrder (modular-plan.md §2.1 and §5 gap resolution #6: drug
transfer, staff deputation and patient referral share one model with a
`kind` discriminator, since architecture.md §3 lists exactly one order
model)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from backend.domain.enums import OrderKind, OrderStatus


class BatchLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_no: str
    quantity: int
    expiry: datetime | None = None


class TransferOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    kind: OrderKind
    from_facility_id: str
    to_facility_id: str
    drug_id: str | None = None
    quantity: int | None = None
    batches: list[BatchLine] = []
    staff_id_hash: str | None = None
    patient_count: int | None = None
    drive_minutes: float
    rationale: str
    forecast_ids: list[str] = []
    status: OrderStatus = OrderStatus.DRAFT
    created_at: datetime
    created_by: str  # "solver" | "agent"
    approved_by: str | None = None
    approved_at: datetime | None = None
    signature: str | None = None
    escalation_level: int = 0

    @model_validator(mode="after")
    def _validate(self) -> "TransferOrder":
        if self.from_facility_id == self.to_facility_id:
            raise ValueError("from_facility_id and to_facility_id must differ")
        if self.created_by not in ("solver", "agent"):
            raise ValueError("created_by must be 'solver' or 'agent'")
        if self.kind == OrderKind.DRUG_TRANSFER:
            if not self.drug_id or self.quantity is None or not self.batches:
                raise ValueError("drug_transfer requires drug_id, quantity and batches")
            if sum(b.quantity for b in self.batches) != self.quantity:
                raise ValueError("batch quantities must sum to quantity")
        if self.signature is not None and self.status == OrderStatus.DRAFT:
            raise ValueError("a draft order may not carry a signature")
        return self
