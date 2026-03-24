from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router

app = FastAPI(
    title="AI Equity Research Agent",
    description="AI Equity Research Agent - Analyze global stocks",
    version="1.0.0",
)

app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def home():
    return FileResponse("app/static/index.html")
