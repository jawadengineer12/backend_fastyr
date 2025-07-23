from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller import User, Chat
from database import engine, Base
from models import User as UserModel  # just to register the model
import uvicorn
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ create tables on startup
    Base.metadata.create_all(bind=engine)
    yield
    # Any shutdown logic here if needed

app = FastAPI(lifespan=lifespan)

app.include_router(User.router)
app.include_router(Chat.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
