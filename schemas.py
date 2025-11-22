"""
SAKSHAM PRAVESH Database Schemas

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercase of the class name.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    password_hash: Optional[str] = Field(None, description="Hashed password")
    role: str = Field("user", description="Role: user/admin")
    is_verified: bool = Field(False, description="Whether OTP/email verified")

class OTPRequest(BaseModel):
    channel: str = Field(..., description="email or phone")
    target: str = Field(..., description="email address or phone number")
    code: str = Field(..., description="6-digit code")
    purpose: str = Field(..., description="signup, login, booking")
    expires_at: datetime = Field(...)
    verified: bool = Field(False)

class Lead(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    source: Optional[str] = Field("website", description="utm/source")
    message: Optional[str] = None
    status: str = Field("new", description="new, contacted, converted, lost")

class Appointment(BaseModel):
    user_email: Optional[EmailStr] = None
    name: str
    phone: Optional[str] = None
    package_id: Optional[str] = None
    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM")
    notes: Optional[str] = None
    status: str = Field("pending", description="pending, confirmed, completed, cancelled")

class Package(BaseModel):
    slug: str
    title: str
    description: str
    features: List[str] = []
    price_inr: int
    is_popular: bool = False

class BlogPost(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: str = "Shreyash Suryawanshi"
    tags: List[str] = []
    published: bool = True
    published_at: Optional[datetime] = None

class Testimonial(BaseModel):
    name: str
    title: Optional[str] = None
    quote: str

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: str
    message: str

class Upload(BaseModel):
    user_email: Optional[EmailStr] = None
    filename: str
    url: str
    purpose: Optional[str] = None
