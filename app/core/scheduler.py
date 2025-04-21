from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.logger import logger

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.start()
    logger.info("APScheduler запущен")
