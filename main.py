from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Product, get_db, init_db
from admin import router as admin_router

app = FastAPI()
app.include_router(admin_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://naino-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()
    db = next(get_db())
    if db.query(Product).count() == 0:
        products = [
            Product(name="Classic Shirt", price=2499, category="Shirts", image="shirt 1.jpg"),
            Product(name="Premium Shirt", price=2799, category="Shirts", image="shirt 3.jpg"),
            Product(name="Tailored Pants", price=3499, category="Bottoms", image="pant 1.jpg"),
            Product(name="Casual Pants", price=3299, category="Bottoms", image="pant 2.jpg"),
            Product(name="Polo Shirt", price=2499, category="Shirts", image="shirt 4.jpg"),
            Product(name="Formal Pants", price=3699, category="Bottoms", image="pant 3.jpg"),
        ]
        db.add_all(products)
        db.commit()

@app.get("/")
def root():
    return {"message": "NAINO Backend Running!"}

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {"error": "Product not found"}
    return product

@app.get("/products/category/{category}")
def get_by_category(category: str, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.category == category).all()