from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class MessageStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"
    RESTORED = "restored"

class ChatType(str, Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"

# Define Models
class Contact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    is_group: bool = False

class ContactCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    is_group: bool = False

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chat_id: str
    sender_name: str
    sender_phone: Optional[str] = None
    content: str
    message_type: str = "text"  # text, image, video, audio, document
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: MessageStatus = MessageStatus.ACTIVE
    deleted_at: Optional[datetime] = None
    whatsapp_message_id: Optional[str] = None
    is_forwarded: bool = False
    reply_to_message_id: Optional[str] = None

class MessageCreate(BaseModel):
    chat_id: str
    sender_name: str
    sender_phone: Optional[str] = None
    content: str
    message_type: str = "text"
    whatsapp_message_id: Optional[str] = None
    is_forwarded: bool = False
    reply_to_message_id: Optional[str] = None

class Chat(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    chat_type: ChatType
    participants: List[str] = []  # List of contact names/phones
    profile_picture: Optional[str] = None
    last_message_time: Optional[datetime] = None
    deleted_messages_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatCreate(BaseModel):
    name: str
    chat_type: ChatType
    participants: List[str] = []
    profile_picture: Optional[str] = None

class DeletedMessageStats(BaseModel):
    total_deleted: int
    today_deleted: int
    this_week_deleted: int
    most_active_chat: Optional[str] = None

# Helper functions
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse datetime strings back from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ['timestamp', 'deleted_at', 'last_message_time', 'created_at'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
    return item

# Routes
@api_router.get("/")
async def root():
    return {"message": "WhatsApp Deleted Messages Monitor API"}

# Chat Management
@api_router.post("/chats", response_model=Chat)
async def create_chat(chat_data: ChatCreate):
    chat_dict = chat_data.dict()
    chat_obj = Chat(**chat_dict)
    chat_mongo = prepare_for_mongo(chat_obj.dict())
    await db.chats.insert_one(chat_mongo)
    return chat_obj

@api_router.get("/chats", response_model=List[Chat])
async def get_chats():
    chats = await db.chats.find().to_list(1000)
    return [Chat(**parse_from_mongo(chat)) for chat in chats]

@api_router.get("/chats/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str):
    chat = await db.chats.find_one({"id": chat_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return Chat(**parse_from_mongo(chat))

# Message Management
@api_router.post("/messages", response_model=Message)
async def create_message(message_data: MessageCreate):
    message_dict = message_data.dict()
    message_obj = Message(**message_dict)
    message_mongo = prepare_for_mongo(message_obj.dict())
    await db.messages.insert_one(message_mongo)
    
    # Update chat's last message time
    await db.chats.update_one(
        {"id": message_data.chat_id},
        {"$set": {"last_message_time": datetime.now(timezone.utc).isoformat()}}
    )
    
    return message_obj

@api_router.get("/messages", response_model=List[Message])
async def get_messages(chat_id: Optional[str] = None, status: Optional[MessageStatus] = None):
    query = {}
    if chat_id:
        query["chat_id"] = chat_id
    if status:
        query["status"] = status
    
    messages = await db.messages.find(query).sort("timestamp", -1).to_list(1000)
    return [Message(**parse_from_mongo(message)) for message in messages]

@api_router.get("/messages/deleted", response_model=List[Message])
async def get_deleted_messages():
    messages = await db.messages.find({"status": MessageStatus.DELETED}).sort("deleted_at", -1).to_list(1000)
    return [Message(**parse_from_mongo(message)) for message in messages]

@api_router.put("/messages/{message_id}/delete")
async def mark_message_deleted(message_id: str):
    result = await db.messages.update_one(
        {"id": message_id},
        {
            "$set": {
                "status": MessageStatus.DELETED,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Update deleted messages count for chat
    message = await db.messages.find_one({"id": message_id})
    if message:
        await db.chats.update_one(
            {"id": message["chat_id"]},
            {"$inc": {"deleted_messages_count": 1}}
        )
    
    return {"status": "success", "message": "Message marked as deleted"}

@api_router.get("/stats", response_model=DeletedMessageStats)
async def get_stats():
    # Get total deleted messages
    total_deleted = await db.messages.count_documents({"status": MessageStatus.DELETED})
    
    # Get today's deleted messages
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_deleted = await db.messages.count_documents({
        "status": MessageStatus.DELETED,
        "deleted_at": {"$gte": today_start.isoformat()}
    })
    
    # Get this week's deleted messages
    week_start = today_start.replace(day=today_start.day - today_start.weekday())
    week_deleted = await db.messages.count_documents({
        "status": MessageStatus.DELETED,
        "deleted_at": {"$gte": week_start.isoformat()}
    })
    
    # Get most active chat (most deleted messages)
    pipeline = [
        {"$match": {"status": MessageStatus.DELETED}},
        {"$group": {"_id": "$chat_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    
    most_active_chat = None
    result = await db.messages.aggregate(pipeline).to_list(1)
    if result:
        chat = await db.chats.find_one({"id": result[0]["_id"]})
        if chat:
            most_active_chat = chat["name"]
    
    return DeletedMessageStats(
        total_deleted=total_deleted,
        today_deleted=today_deleted,
        this_week_deleted=week_deleted,
        most_active_chat=most_active_chat
    )

# Contact Management
@api_router.post("/contacts", response_model=Contact)
async def create_contact(contact_data: ContactCreate):
    contact_dict = contact_data.dict()
    contact_obj = Contact(**contact_dict)
    await db.contacts.insert_one(contact_obj.dict())
    return contact_obj

@api_router.get("/contacts", response_model=List[Contact])
async def get_contacts():
    contacts = await db.contacts.find().to_list(1000)
    return [Contact(**contact) for contact in contacts]

# Initialize with sample data
@api_router.post("/init-sample-data")
async def initialize_sample_data():
    # Check if data already exists
    existing_chats = await db.chats.count_documents({})
    if existing_chats > 0:
        return {"message": "Sample data already exists"}
    
    # Sample contacts
    contacts = [
        Contact(name="John Doe", phone="+1234567890", profile_picture="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face"),
        Contact(name="Jane Smith", phone="+1987654321", profile_picture="https://images.unsplash.com/photo-1494790108755-2616b332c58e?w=100&h=100&fit=crop&crop=face"),
        Contact(name="Family Group", is_group=True, profile_picture="https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=100&h=100&fit=crop"),
    ]
    
    # Sample chats
    chats = [
        Chat(
            id="chat-1",
            name="John Doe",
            chat_type=ChatType.INDIVIDUAL,
            participants=["John Doe"],
            profile_picture="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face",
            deleted_messages_count=3
        ),
        Chat(
            id="chat-2", 
            name="Family Group",
            chat_type=ChatType.GROUP,
            participants=["Mom", "Dad", "Sister"],
            profile_picture="https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=100&h=100&fit=crop",
            deleted_messages_count=2
        ),
        Chat(
            id="chat-3",
            name="Jane Smith", 
            chat_type=ChatType.INDIVIDUAL,
            participants=["Jane Smith"],
            profile_picture="https://images.unsplash.com/photo-1494790108755-2616b332c58e?w=100&h=100&fit=crop&crop=face",
            deleted_messages_count=1
        )
    ]
    
    # Sample messages (including deleted ones)
    messages = [
        Message(
            chat_id="chat-1",
            sender_name="John Doe",
            content="Hey! How are you doing?",
            status=MessageStatus.DELETED,
            deleted_at=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc).replace(hour=10, minute=30)
        ),
        Message(
            chat_id="chat-1", 
            sender_name="John Doe",
            content="I think I said something wrong earlier...", 
            status=MessageStatus.DELETED,
            deleted_at=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc).replace(hour=11, minute=15)
        ),
        Message(
            chat_id="chat-1",
            sender_name="John Doe", 
            content="Sorry for the confusion, let me clarify",
            status=MessageStatus.DELETED,
            deleted_at=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc).replace(hour=12, minute=0)
        ),
        Message(
            chat_id="chat-2",
            sender_name="Mom",
            content="Don't forget about dinner tomorrow!",
            status=MessageStatus.DELETED, 
            deleted_at=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc).replace(hour=15, minute=30)
        ),
        Message(
            chat_id="chat-2",
            sender_name="Dad",
            content="I might be running late from work",
            status=MessageStatus.DELETED,
            deleted_at=datetime.now(timezone.utc), 
            timestamp=datetime.now(timezone.utc).replace(hour=16, minute=45)
        ),
        Message(
            chat_id="chat-3",
            sender_name="Jane Smith",
            content="Can we reschedule our meeting?",
            status=MessageStatus.DELETED,
            deleted_at=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc).replace(hour=14, minute=20)
        )
    ]
    
    # Insert sample data
    for contact in contacts:
        await db.contacts.insert_one(contact.dict())
    
    for chat in chats:
        await db.chats.insert_one(prepare_for_mongo(chat.dict()))
        
    for message in messages:
        await db.messages.insert_one(prepare_for_mongo(message.dict()))
    
    return {"message": "Sample data initialized successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()