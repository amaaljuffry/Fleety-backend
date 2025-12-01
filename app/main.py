from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import get_database, close_database
from app.routes import auth, vehicles, maintenance, reminders, settings as settings_routes, contact, public_contact, faq, support, newsletter, waitlist, vehicle_positions, drivers, fuel, stripe, documents
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fleety API",
    description="Vehicle Maintenance Log API",
    version="1.0.0"
)

# Add CORS middleware - must be added first for proper request handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=".*",  # Accept all origin patterns
)

# Mount public folder for static files
public_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
if os.path.exists(public_dir):
    app.mount("/public", StaticFiles(directory=public_dir), name="public")


# Include routers
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(maintenance.router)
app.include_router(reminders.router)
app.include_router(settings_routes.router)
app.include_router(contact.router)
app.include_router(public_contact.router)
app.include_router(faq.router)
app.include_router(support.router)
app.include_router(newsletter.router)
app.include_router(waitlist.router)
app.include_router(vehicle_positions.router)
app.include_router(drivers.router)
app.include_router(fuel.router)
app.include_router(stripe.router)
app.include_router(documents.router)


# Lifecycle events
@app.on_event("startup")
async def startup():
    logger.info("Starting Fleety API")
    # Initialize database connection
    get_database()


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Fleety API")
    close_database()


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to Fleety API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
