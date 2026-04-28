from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    prompts,
    criteria,
    conversations,
    analyses,
    auth,
    users,
)

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


app.include_router(auth.router)
app.include_router(users.router)

app.include_router(prompts.router)
app.include_router(criteria.router)
app.include_router(conversations.router)
app.include_router(analyses.router)
