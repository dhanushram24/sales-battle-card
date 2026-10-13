import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router
from app.core.security import protect_request
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Enterprise Sales Battlecard & Semantic Sentiment Scoring API for Paramantra CRM",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (Allows your Paramantra client React app to call this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(protect_request)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logging.getLogger(__name__).error("Database operation failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Check the database connection and schema."})

# Mount Frontend React build
backend_root = os.path.dirname(os.path.dirname(__file__))
project_root = os.path.dirname(backend_root)
frontend_dist = os.path.join(project_root, "frontend", "dist")

if os.path.exists(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

# Register API routes
app.include_router(router)


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(os.path.join(frontend_dist, "favicon.svg"))


@app.get("/", include_in_schema=False)
def root():
    # Serve built React frontend if available
    react_index = os.path.join(frontend_dist, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index)

    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG)
