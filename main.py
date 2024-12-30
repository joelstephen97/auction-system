from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import uuid4
from sqlalchemy import create_engine, Column, String, Float, Table, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = "sqlite:///./auction.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database models
class AdminModel(Base):
    __tablename__ = "admins"
    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)

class AuctionItemModel(Base):
    __tablename__ = "auction_items"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    starting_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    highest_bidder = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# Models
class AuctionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    starting_price: float
    current_price: float
    highest_bidder: Optional[str] = None

class Bid(BaseModel):
    user: str
    bid_amount: float

class Admin(BaseModel):
    username: str
    password: str

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for admin authentication
def get_admin(db: SessionLocal, username: str, password: str):
    admin = db.query(AdminModel).filter(AdminModel.username == username).first()
    if admin and pwd_context.verify(password, admin.hashed_password):
        return admin
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/admin/register/")
def register_admin(admin: Admin, db: SessionLocal = Depends(get_db)):
    hashed_password = pwd_context.hash(admin.password)
    db_admin = AdminModel(username=admin.username, hashed_password=hashed_password)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return {"detail": "Admin registered successfully"}

@app.post("/admin/auctions/", response_model=AuctionItem)
def create_auction(item: AuctionItem, username: str, password: str, db: SessionLocal = Depends(get_db)):
    get_admin(db, username, password)
    db_item = AuctionItemModel(
        id=item.id,
        name=item.name,
        description=item.description,
        starting_price=item.starting_price,
        current_price=item.starting_price
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return item

@app.delete("/admin/auctions/{item_id}")
def delete_auction(item_id: str, username: str, password: str, db: SessionLocal = Depends(get_db)):
    get_admin(db, username, password)
    item = db.query(AuctionItemModel).filter(AuctionItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Auction item not found.")
    db.delete(item)
    db.commit()
    return {"detail": "Auction item deleted successfully"}

@app.get("/auctions/", response_model=List[AuctionItem])
def list_auctions(db: SessionLocal = Depends(get_db)):
    items = db.query(AuctionItemModel).all()
    return [AuctionItem(
        id=item.id,
        name=item.name,
        description=item.description,
        starting_price=item.starting_price,
        current_price=item.current_price,
        highest_bidder=item.highest_bidder
    ) for item in items]

@app.get("/auctions/{item_id}", response_model=AuctionItem)
def get_auction(item_id: str, db: SessionLocal = Depends(get_db)):
    item = db.query(AuctionItemModel).filter(AuctionItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Auction item not found.")
    return AuctionItem(
        id=item.id,
        name=item.name,
        description=item.description,
        starting_price=item.starting_price,
        current_price=item.current_price,
        highest_bidder=item.highest_bidder
    )

@app.websocket("/auctions/{item_id}/bid")
async def auction_bid_websocket(websocket: WebSocket, item_id: str, db: SessionLocal = Depends(get_db)):
    await websocket.accept()
    item = db.query(AuctionItemModel).filter(AuctionItemModel.id == item_id).first()
    if not item:
        await websocket.close(code=1003, reason="Auction item not found.")
        return

    while True:
        try:
            data = await websocket.receive_json()
            bid = Bid(**data)

            if bid.bid_amount <= item.current_price:
                await websocket.send_json({"error": "Bid amount must be higher than the current price."})
                continue

            # Update auction item with new bid
            item.current_price = bid.bid_amount
            item.highest_bidder = bid.user
            db.commit()

            # Notify all connected clients (broadcast)
            for connection in websocket.app.state.active_connections[item_id]:
                await connection.send_json({
                    "item_id": item.id,
                    "current_price": item.current_price,
                    "highest_bidder": item.highest_bidder,
                })
        except Exception as e:
            await websocket.close(code=1000, reason=str(e))
            break

@app.on_event("startup")
def setup():
    app.state.active_connections: Dict[str, List[WebSocket]] = {}
    for item_id in []:
        app.state.active_connections[item_id] = []

@app.on_event("shutdown")
def cleanup():
    app.state.active_connections.clear()
