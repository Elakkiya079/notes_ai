from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import connect
from app.routes.auth import router as auth_router
from app.routes.github import router as github_router
from app.routes.imports import router as import_router
from app.routes.notes import router as notes_router


@asynccontextmanager
async def lifespan(_app):
    try:
        connect()
    except Exception as error:
        print(f"Could not connect to MongoDB. {error}")
        raise
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request, _exc):
    return JSONResponse(status_code=400, content={"error": "Check the form and try again."})


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(auth_router)
app.include_router(github_router)
app.include_router(import_router)
app.include_router(notes_router)
