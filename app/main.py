from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from app.api.routes import users, attendance, camera, auth, mobile, periods
from app.config import config
from app.services.period_scheduler import PeriodSchedulerService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Face Recognition Attendance System",
    version="1.0.0",
    description="Mobile-ready face attendance API with authentication"
)

scheduler = BackgroundScheduler(timezone=config.TIMEZONE)

# Configure CORS for mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your mobile app domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(mobile.router, prefix="/api/v1/mobile", tags=["mobile"])
app.include_router(camera.router, prefix="/api/v1/camera", tags=["camera"])
app.include_router(periods.router, prefix="/api/v1/periods", tags=["periods"])


def _run_period_job():
    service = PeriodSchedulerService()
    result = service.run_period_end_checks()
    logger.info(
        "Period scheduler run complete | processed=%s absent_marked=%s emails_sent=%s",
        result.get("processed_periods", 0),
        result.get("absent_marked", 0),
        result.get("emails_sent", 0),
    )


@app.on_event("startup")
def start_background_scheduler():
    if scheduler.running:
        logger.info("Background scheduler already running")
        return

    scheduler.add_job(
        _run_period_job,
        trigger=IntervalTrigger(minutes=1),
        id="period_end_checks",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Background scheduler started (interval=1 minute, timezone=%s)", config.TIMEZONE)


@app.on_event("shutdown")
def stop_background_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "message": "Face Attendance API is running"}

@app.get("/")
async def root():
    return {
        "app": "Face Recognition Attendance System",
        "version": "1.0.0",
        "mobile_ready": True,
        "docs": "/docs"
    }