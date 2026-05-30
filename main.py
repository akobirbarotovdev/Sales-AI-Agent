import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from database import init_db
from api.routes import router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sales Agent Tizimi v1.0",
    description="Multi-agent AI system for lead generation in Uzbekistan",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
