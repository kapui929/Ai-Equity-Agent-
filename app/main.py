from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router

app = FastAPI(
    title="AI Equity Research Agent",
    description="AI Equity Research Agent - Analyze global stocks",
    version="1.0.0",
)

# 1. API 路由放最前面
app.include_router(router)

# 2. 首頁
@app.get("/")
def home():
    return FileResponse("app/static/index.html")

# 3. 靜態文件放最後
app.mount("/static", StaticFiles(directory="app/static"), name="static")
