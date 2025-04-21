from fastapi import APIRouter
from app.services import categories, products, modifications
from app.logger import logger

router = APIRouter()

@router.get("/health")
async def health():
    logger.info("Healthcheck пройден")
    return {"status": "ok"}
