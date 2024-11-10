from fastapi import APIRouter
from typing import List

from sandbox.packs import PACKS, StackPack

router = APIRouter(prefix="/api/stacks", tags=["stacks"])


@router.get("", response_model=List[StackPack])
async def get_stack_packs():
    """
    Get all available stack packs that can be used as templates for new projects.
    """
    return PACKS
