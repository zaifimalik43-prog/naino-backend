from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from pydantic import BaseModel
from typing import Optional, List, Any
from database import Product, Order, get_db
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["admin"])


# ─────────────────────────────────────────
# PRODUCT SCHEMAS
# ─────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    price: float
    category: str
    image: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image: Optional[str] = None


# ─────────────────────────────────────────
# PRODUCT ROUTES
# ─────────────────────────────────────────

@router.get("/products")
def get_all_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@router.post("/products")
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.put("/products/{product_id}")
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in product.model_dump(exclude_none=True).items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}


# ─────────────────────────────────────────
# ORDER SCHEMAS
# ─────────────────────────────────────────

class OrderCreate(BaseModel):
    customer_name: str
    customer_email: Optional[str] = ""
    customer_phone: str
    address: str
    city: str
    province: str
    payment_method: str
    total: float
    items: List[Any]

class OrderStatusUpdate(BaseModel):
    status: str  # pending / confirmed / shipped / delivered / cancelled


# ─────────────────────────────────────────
# ORDER ROUTES
# ─────────────────────────────────────────

@router.post("/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    new_order = Order(**order.model_dump())
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@router.get("/orders")
def get_all_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return orders

@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    valid = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    order.status = body.status
    db.commit()
    db.refresh(order)
    return order


# ─────────────────────────────────────────
# STATS & GRAPH ROUTES
# ─────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    confirmed_orders = db.query(Order).filter(Order.status == "confirmed").count()

    # Revenue = only confirmed + shipped + delivered orders
    revenue_result = db.query(func.sum(Order.total)).filter(
        Order.status.in_(["confirmed", "shipped", "delivered"])
    ).scalar()
    total_revenue = revenue_result or 0

    return {
        "total_products": total_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "total_revenue": total_revenue,
    }

@router.get("/sales/daily")
def get_daily_sales(db: Session = Depends(get_db)):
    """Returns last 7 days sales (confirmed/shipped/delivered only)"""
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    result = []
    for day in days:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())

        total = db.query(func.sum(Order.total)).filter(
            Order.status.in_(["confirmed", "shipped", "delivered"]),
            Order.created_at >= day_start,
            Order.created_at <= day_end,
        ).scalar() or 0

        order_count = db.query(func.count(Order.id)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
        ).scalar() or 0

        result.append({
            "date": day.strftime("%d %b"),
            "revenue": round(total),
            "orders": order_count,
        })

    return result
