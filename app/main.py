from fastapi import FastAPI

from app.router import router

app = FastAPI(
    title="PDF Compare API",
    description="REST API to compare visible text content between two PDF files.",
    version="1.0.0",
)

app.include_router(router)
