
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import (
    InventoryItem,
    InventoryMovement,
    MovementType,
)
from app.models.user import User
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    StockMovementCreate,
)


def create_item(
    db: Session,
    payload: InventoryItemCreate,
    current_user: User,
) -> InventoryItem:
    item = InventoryItem(
        **payload.model_dump(),
        quantity=0,
        created_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: int) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise ValueError("Inventory item not found")
    return item


def list_items(
    db: Session,
    category=None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[InventoryItem]:
    query = select(InventoryItem)

    if category is not None:
        query = query.where(InventoryItem.category == category)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(InventoryItem.name.ilike(term))

    query = query.order_by(InventoryItem.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def update_item(
    db: Session,
    item_id: int,
    payload: InventoryItemUpdate,
) -> InventoryItem:
    item = get_item(db, item_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


def _record_movement(
    db: Session,
    item: InventoryItem,
    movement_type: MovementType,
    payload: StockMovementCreate,
    current_user: User,
) -> InventoryMovement:
    if movement_type == MovementType.RECEIVED:
        new_quantity = item.quantity + payload.quantity
    elif movement_type == MovementType.ISSUED:
        if payload.quantity > item.quantity:
            raise ValueError(
                f"Insufficient stock. Available quantity: {item.quantity}"
            )
        new_quantity = item.quantity - payload.quantity
    else:
        raise ValueError("Unsupported stock movement type")

    movement = InventoryMovement(
        item_id=item.id,
        movement_type=movement_type,
        quantity=payload.quantity,
        quantity_after=new_quantity,
        reference=payload.reference,
        notes=payload.notes,
        performed_by=current_user.id,
    )

    item.quantity = new_quantity
    db.add(movement)
    db.commit()
    db.refresh(movement)
    db.refresh(item)
    return movement


def receive_stock(
    db: Session,
    item_id: int,
    payload: StockMovementCreate,
    current_user: User,
) -> InventoryMovement:
    item = get_item(db, item_id)
    return _record_movement(
        db, item, MovementType.RECEIVED, payload, current_user
    )


def issue_stock(
    db: Session,
    item_id: int,
    payload: StockMovementCreate,
    current_user: User,
) -> InventoryMovement:
    item = get_item(db, item_id)
    return _record_movement(
        db, item, MovementType.ISSUED, payload, current_user
    )


def list_movements(
    db: Session,
    item_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[InventoryMovement]:
    get_item(db, item_id)

    query = (
        select(InventoryMovement)
        .where(InventoryMovement.item_id == item_id)
        .order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query).all())
