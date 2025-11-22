import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt

from database import db, create_document, get_documents
from schemas import User, Lead, Appointment, Package, BlogPost, Testimonial, ContactMessage, OTPRequest, Upload

APP_NAME = "SAKSHAM PRAVESH"
JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGO = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title=APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.user.find_one({"email": email}) if db else None
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"email": user["email"], "name": user.get("name"), "role": user.get("role", "user")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
def root():
    return {"message": f"{APP_NAME} API running"}

# Auth & OTP (basic dev OTP flow)

class OTPStart(BaseModel):
    channel: str
    target: str
    purpose: str

class OTPVerify(BaseModel):
    target: str
    code: str
    purpose: str

@app.post("/auth/register", response_model=Token)
def register(name: str = Form(...), email: EmailStr = Form(...), password: str = Form(...)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    if db.user.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=name, email=email, password_hash=hash_password(password))
    create_document("user", user)
    token = create_token({"sub": email})
    return Token(access_token=token)

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    user = db.user.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_token({"sub": user["email"]})
    return Token(access_token=token)

@app.post("/auth/otp/start")
def otp_start(body: OTPStart):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Dev OTP code 123456; In production integrate with SMS/Email provider
    record = OTPRequest(channel=body.channel, target=body.target, code="123456", purpose=body.purpose, expires_at=datetime.utcnow() + timedelta(minutes=10))
    create_document("otprequest", record)
    return {"sent": True, "dev_code": "123456"}

@app.post("/auth/otp/verify")
def otp_verify(body: OTPVerify):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    req = db.otprequest.find_one({"target": body.target, "code": body.code, "purpose": body.purpose})
    if not req:
        raise HTTPException(status_code=400, detail="Invalid code")
    return {"verified": True}

# Packages & public content

@app.get("/packages", response_model=List[Package])
def list_packages():
    if not db:
        return []
    docs = get_documents("package")
    return [Package(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.post("/packages")
def create_package(pkg: Package, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    create_document("package", pkg)
    return {"ok": True}

@app.get("/blog", response_model=List[BlogPost])
def list_posts():
    if not db:
        return []
    docs = get_documents("blogpost")
    return [BlogPost(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.post("/blog")
def create_post(post: BlogPost, user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    create_document("blogpost", post)
    return {"ok": True}

# Leads, Appointments, Contact

@app.post("/lead")
def create_lead(lead: Lead):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    create_document("lead", lead)
    return {"ok": True}

@app.post("/appointment")
def create_appointment(appt: Appointment):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    create_document("appointment", appt)
    return {"ok": True}

@app.get("/admin/leads")
def admin_leads(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    docs = get_documents("lead")
    return docs

@app.get("/admin/appointments")
def admin_appointments(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    docs = get_documents("appointment")
    return docs

# File Upload (placeholder URL)

@app.post("/upload")
def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    content = file.filename  # In production, upload to S3/Cloudinary
    record = Upload(user_email=user.get("email"), filename=file.filename, url=f"/uploads/{content}")
    create_document("upload", record)
    return {"url": record.url}

# Payments (client will create order via Razorpay/Stripe on frontend; backend can verify webhook later)

class PaymentInit(BaseModel):
    package_slug: str

@app.post("/payments/init")
def payment_init(body: PaymentInit, user=Depends(get_current_user)):
    # For demo, return a mock order id; integrate with Razorpay/Stripe later
    return {"order_id": f"ORDER_{datetime.utcnow().timestamp()}", "amount": 0}

# Test endpoint (kept from template)

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
