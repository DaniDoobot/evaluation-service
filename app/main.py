from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import prompts, criteria, conversations, analyses

app = FastAPI(
    title="Conversation Evaluation Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo restringimos al dominio del front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(prompts.router)
app.include_router(criteria.router)
app.include_router(conversations.router)
app.include_router(analyses.router)

class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255))
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
