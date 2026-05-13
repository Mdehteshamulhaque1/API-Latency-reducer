"""
Cache rules management API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_session
from app.schemas.rules import CacheRuleCreate, CacheRuleUpdate, CacheRuleResponse
from app.core.security import verify_role
from app.core.exceptions import APIException
from app.models import CacheRule
from sqlalchemy.future import select

router = APIRouter(prefix="/rules", tags=["Cache Rules"])


@router.get("", response_model=List[CacheRuleResponse])
async def list_rules(
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    """List all cache rules."""
    try:
        result = await session.execute(
            select(CacheRule).offset(skip).limit(limit)
        )
        rules = result.scalars().all()
        return [CacheRuleResponse.from_orm(rule) for rule in rules]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=CacheRuleResponse)
async def create_rule(
    rule_data: CacheRuleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(verify_role(["admin", "operator"])),
):
    """Create a new cache rule."""
    try:
        rule = CacheRule(**rule_data.dict())
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return CacheRuleResponse.from_orm(rule)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}", response_model=CacheRuleResponse)
async def get_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific cache rule."""
    try:
        result = await session.execute(
            select(CacheRule).where(CacheRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        return CacheRuleResponse.from_orm(rule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}", response_model=CacheRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: CacheRuleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(verify_role(["admin", "operator"])),
):
    """Update a cache rule."""
    try:
        result = await session.execute(
            select(CacheRule).where(CacheRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        # Update fields
        update_data = rule_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        await session.commit()
        await session.refresh(rule)

        return CacheRuleResponse.from_orm(rule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(verify_role(["admin"])),
):
    """Delete a cache rule."""
    try:
        result = await session.execute(
            select(CacheRule).where(CacheRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        await session.delete(rule)
        await session.commit()

        return {"message": "Rule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
