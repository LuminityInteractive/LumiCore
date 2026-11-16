from fastapi import FastAPI

app = FastAPI(
    title="LumiCore",
    description="Open-source backend infrastructure for modern applications.",
    version="0.0.1",
)

@app.get("/")
async def root():
    return {
        "name" : "LumiCore",
        "version" : "0.0.1",
        "status" : "running",
    }

@app.get("/health")
async def health():
    return {
        "status" : "healthy",
    }
