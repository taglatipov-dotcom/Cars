import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.auth import get_current_admin
from src.email_notifier import notify_new_lead
from src.schemas import (
    LeadStatus,
    SDeleteLeadResult,
    SLead,
    SLeadId,
    SLeadSubmit,
    SLeadUpdate,
)

router = APIRouter(prefix="/leads", tags=["Заявки"])

DATA_PATH = Path(__file__).parent / "data" / "leads.json"


def _load_leads() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_leads(leads: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)


# ---------- Публичный: создать заявку ----------

@router.post("", response_model=SLeadId, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: SLeadSubmit,
    background: BackgroundTasks,
) -> dict:
    leads = _load_leads()
    new_id = max((l.get("id", 0) for l in leads), default=0) + 1

    item = {
        "id": new_id,
        **data.model_dump(),
        "status": LeadStatus.new.value,
        "comment": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    leads.append(item)
    _save_leads(leads)

    # Отправка письма в фоне — не тормозит ответ пользователю.
    # Если SMTP не настроен или упал — заявка всё равно сохранена.
    background.add_task(notify_new_lead, item)

    return {"ok": True, "lead_id": new_id}


# ---------- Только админ: список ----------

@router.get("", response_model=list[SLead])
async def get_leads(
    _admin: str = Depends(get_current_admin),
) -> list[dict]:
    return sorted(_load_leads(), key=lambda l: l.get("id", 0), reverse=True)


# ---------- Только админ: одна ----------

@router.get("/{lead_id}", response_model=SLead)
async def get_lead(
    lead_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    for l in _load_leads():
        if l.get("id") == lead_id:
            return l
    raise HTTPException(status_code=404, detail="Lead not found")


# ---------- Только админ: обновить ----------

@router.patch("/{lead_id}", response_model=SLead)
async def update_lead(
    lead_id: int,
    data: SLeadUpdate,
    _admin: str = Depends(get_current_admin),
) -> dict:
    leads = _load_leads()
    patch = {
        k: (v.value if isinstance(v, LeadStatus) else v)
        for k, v in data.model_dump().items()
        if v is not None
    }

    for idx, l in enumerate(leads):
        if l.get("id") == lead_id:
            leads[idx] = {**l, **patch}
            _save_leads(leads)
            return leads[idx]

    raise HTTPException(status_code=404, detail="Lead not found")


# ---------- Только админ: удалить ----------

@router.delete("/{lead_id}", response_model=SDeleteLeadResult)
async def delete_lead(
    lead_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    leads = _load_leads()
    new_list = [l for l in leads if l.get("id") != lead_id]

    if len(new_list) == len(leads):
        raise HTTPException(status_code=404, detail="Lead not found")

    _save_leads(new_list)
    return {"ok": True, "lead_id": lead_id}