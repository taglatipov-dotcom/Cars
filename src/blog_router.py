import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth import get_current_admin
from src.schemas import (
    SBlog,
    SBlogAdd,
    SBlogId,
    SBlogPreview,
    SBlogUpdate,
    SDeleteBlogResult,
)

router = APIRouter(prefix="/blog", tags=["Блог"])

DATA_PATH = Path(__file__).parent / "data" / "blogs.json"


# ---------- Внутренние хелперы ----------

def _load_blogs() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_blogs(blogs: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(blogs, f, ensure_ascii=False, indent=2)


# ---------- Список статей (превью, без content) ----------

@router.get("", response_model=list[SBlogPreview])
async def get_blogs() -> list[dict]:
    blogs = _load_blogs()
    return [
        {k: v for k, v in blog.items() if k != "content"}
        for blog in blogs
    ]


# ---------- Одна статья по slug (внимание: до /{blog_id}) ----------

@router.get("/slug/{slug}", response_model=SBlog)
async def get_blog_by_slug(slug: str) -> dict:
    for blog in _load_blogs():
        if blog.get("slug") == slug:
            return blog
    raise HTTPException(status_code=404, detail="Blog not found")


# ---------- Одна статья по id ----------

@router.get("/{blog_id}", response_model=SBlog)
async def get_blog(blog_id: int) -> dict:
    for blog in _load_blogs():
        if blog.get("id") == blog_id:
            return blog
    raise HTTPException(status_code=404, detail="Blog not found")


# ---------- Создание (только админ) ----------

@router.post("", response_model=SBlogId, status_code=status.HTTP_201_CREATED)
async def add_blog(
    blog: SBlogAdd,
    _admin: str = Depends(get_current_admin),
) -> dict:
    blogs = _load_blogs()

    # Проверим уникальность slug
    if any(b.get("slug") == blog.slug for b in blogs):
        raise HTTPException(
            status_code=400,
            detail=f"Slug '{blog.slug}' уже используется",
        )

    new_id = max((b.get("id", 0) for b in blogs), default=0) + 1
    item = {"id": new_id, **blog.model_dump()}
    blogs.append(item)
    _save_blogs(blogs)
    return {"ok": True, "blog_id": new_id}


# ---------- Обновление (только админ) ----------

@router.patch("/{blog_id}", response_model=SBlog)
async def update_blog(
    blog_id: int,
    data: SBlogUpdate,
    _admin: str = Depends(get_current_admin),
) -> dict:
    blogs = _load_blogs()

    # Проверим уникальность нового slug (если меняется)
    patch = {k: v for k, v in data.model_dump().items() if v is not None}
    new_slug = patch.get("slug")
    if new_slug:
        conflict = any(
            b.get("slug") == new_slug and b.get("id") != blog_id
            for b in blogs
        )
        if conflict:
            raise HTTPException(
                status_code=400,
                detail=f"Slug '{new_slug}' уже используется",
            )

    for idx, b in enumerate(blogs):
        if b.get("id") == blog_id:
            blogs[idx] = {**b, **patch}
            _save_blogs(blogs)
            return blogs[idx]

    raise HTTPException(status_code=404, detail="Blog not found")


# ---------- Удаление (только админ) ----------

@router.delete("/{blog_id}", response_model=SDeleteBlogResult)
async def delete_blog(
    blog_id: int,
    _admin: str = Depends(get_current_admin),
) -> dict:
    blogs = _load_blogs()
    new_list = [b for b in blogs if b.get("id") != blog_id]

    if len(new_list) == len(blogs):
        raise HTTPException(status_code=404, detail="Blog not found")

    _save_blogs(new_list)
    return {"ok": True, "blog_id": blog_id}