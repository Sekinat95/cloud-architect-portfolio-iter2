from fastapi import FastAPI

app = FastAPI(title="Backend API Project")

@app.get("/health")
def health():
    return {"status": "ok"}