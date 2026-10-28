
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.inventory import InventoryCategory, InventoryItem, InventoryMovement
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryMovementResponse,
    StockMovementCreate,
)
from app.services.inventory import (
    create_item,
    get_item,
    issue_stock,
    list_items,
    list_movements,
    receive_stock,
    update_item,
)

router = APIRouter(prefix="/inventory", tags=["Resource Inventory"])

INVENTORY_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.FINANCE_OFFICER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "/items",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_item(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*INVENTORY_ROLES)),
):
    return create_item(db, payload, current_user)


@router.get("/items", response_model=list[InventoryItemResponse])
def get_inventory_items(
    category: InventoryCategory | None = None,
    search: str | None = Query(default=None, max_length=150),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_items(db, category, search, skip, limit)


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_item(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/items/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*INVENTORY_ROLES)),
):
    try:
        return update_item(db, item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/items/{item_id}/receive",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def receive_inventory_stock(
    item_id: int,
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*INVENTORY_ROLES)),
):
    try:
        return receive_stock(db, item_id, payload, current_user)
    except ValueError as exc:
        code = 404 if str(exc) == "Inventory item not found" else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post(
    "/items/{item_id}/issue",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_inventory_stock(
    item_id: int,
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*INVENTORY_ROLES)),
):
    try:
        return issue_stock(db, item_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Inventory item not found" else 400
        raise HTTPException(status_code=code, detail=message) from exc


@router.get(
    "/items/{item_id}/movements",
    response_model=list[InventoryMovementResponse],
)
def get_inventory_movements(
    item_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return list_movements(db, item_id, skip, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.NGO_MANAGER)
    ),
):
    try:
        item = get_item(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    has_movements = db.scalar(
        select(InventoryMovement.id)
        .where(InventoryMovement.item_id == item_id)
        .limit(1)
    )

    if item.quantity != 0 or has_movements is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an item with stock or movement history",
        )

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
