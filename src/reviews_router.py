import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth import get_current_admin
from src.schemas import (
    SDeleteReviewResult,
    SPendingReview,
    SReview,
    SReviewAdd,
    SReviewId,
    SReviewSubmit,
    SReviewUpdate,
)

router = APIRouter(prefix="/reviews", tags=["Отзывы"])

DATA_PATH = Path(__file__).parent / "data" / "reviews.json"
PENDING_PATH = Path(__file__).parent / "data" / "pending_reviews.json"


# ---------- Внутренние хелперы ----------

def _load_reviews() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_reviews(reviews: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


def _load_pending() -> list[dict]:
    if not PENDING_PATH.exists():
        return []
    with PENDING_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_pending(items: list[dict]) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PENDING_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ============================================================
# ВАЖНО: маршруты со статичными сегментами (/submit, /pending)
# объявлены РАНЬШЕ, чем /{review_id} — иначе FastAPI попытается
# распарсить строку «submit» / «pending» как int и вернёт 422.
# ============================================================


# ---------- Чтение всех (публичный) ----------

@router.get("", response_model=list[SReview])
async def get_reviews() -> list[dict]:
    return _load_reviews()


# ---------- Отправка отзыва посетителем (публичный, без авторизации) ----------

@router.post("/submit", response_model=SPendingReview, status_code=status.HTTP_201_CREATED)
async def submit_review(data: SReviewSubmit) -> dict:
    pending = _load_pending()
    new_id = max((p.get("id", 0) for p in pending), default=0) + 1
    item = {
        "id": new_id,
        **data.model_dump(),
        "avatar": None,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    pending.append(item)
    _save_pending(pending)
    return item


# ---------- Модерация: список ожидающих (только админ) ----------

@router.get("/pending", response_model=list[SPendingReview])
async def get_pending_reviews(
    _admin: str = Depends(get_current_admin),
) -> list[dict]:
    return _load_pending()


# ---------- Модерация: одобрить → перенести в основной список (только админ) ----------

@router.post(
    "/pending/{review_id}/approve",
    response_model=SReview,
    status_code=status.HTTP_201_CREATED,
)
async def approve_review(
    review_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    pending = _load_pending()
    target = next((p for p in pending if p.get("id") == review_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Pending review not found")

    reviews = _load_reviews()
    new_id = max((r.get("id", 0) for r in reviews), default=0) + 1

    new_review = {
        "id": new_id,
        "name": target["name"],
        "avatar": target.get("avatar") or f"https://i.pravatar.cc/150?u=review{new_id}",
        "rating": target["rating"],
        "text": target["text"],
        "car": target["car"],
        "photos": target.get("photos") or [],
    }
    reviews.append(new_review)
    _save_reviews(reviews)

    # Удаляем из очереди
    _save_pending([p for p in pending if p.get("id") != review_id])

    return new_review


# ---------- Модерация: отклонить (только админ) ----------

@router.delete("/pending/{review_id}", response_model=SDeleteReviewResult)
async def reject_review(
    review_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    pending = _load_pending()
    new_list = [p for p in pending if p.get("id") != review_id]

    if len(new_list) == len(pending):
        raise HTTPException(status_code=404, detail="Pending review not found")

    _save_pending(new_list)
    return {"ok": True, "review_id": review_id}


# ---------- Чтение одного (публичный) ----------

@router.get("/{review_id}", response_model=SReview)
async def get_review(review_id: int) -> dict:
    for r in _load_reviews():
        if r.get("id") == review_id:
            return r
    raise HTTPException(status_code=404, detail="Review not found")


# ---------- Создание напрямую админом (только админ) ----------

@router.post("", response_model=SReviewId, status_code=status.HTTP_201_CREATED)
async def add_review(
    review: SReviewAdd,
    _admin: str = Depends(get_current_admin),
) -> dict:
    reviews = _load_reviews()
    new_id = max((r.get("id", 0) for r in reviews), default=0) + 1
    item = {"id": new_id, **review.model_dump()}
    reviews.append(item)
    _save_reviews(reviews)
    return {"ok": True, "review_id": new_id}


# ---------- Обновление (только админ) ----------

@router.patch("/{review_id}", response_model=SReview)
async def update_review(
    review_id: int,
    data: SReviewUpdate,
    _admin: str = Depends(get_current_admin),
) -> dict:
    reviews = _load_reviews()
    patch = {k: v for k, v in data.model_dump().items() if v is not None}

    for idx, r in enumerate(reviews):
        if r.get("id") == review_id:
            reviews[idx] = {**r, **patch}
            _save_reviews(reviews)
            return reviews[idx]

    raise HTTPException(status_code=404, detail="Review not found")


# ---------- Удаление (только админ) ----------

@router.delete("/{review_id}", response_model=SDeleteReviewResult)
async def delete_review(
    review_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    reviews = _load_reviews()
    new_list = [r for r in reviews if r.get("id") != review_id]

    if len(new_list) == len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")

    _save_reviews(new_list)
    return {"ok": True, "review_id": review_id}

