from fastapi import FastAPI
from app.api import routes
from app.core.scheduler import scheduler, start_scheduler
from app.services import categories, products, modifications
from app.core import config
from app.db.supabase_client import supabase
from app.logger import logger

app = FastAPI()
app.include_router(routes.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Запуск планировщика и приложения")
    start_scheduler()

    scheduler.add_job(categories.sync_categories, "interval", seconds=config.SYNC_INTERVAL_SECONDS)
    scheduler.add_job(products.sync_products, "interval", seconds=config.SYNC_INTERVAL_SECONDS)
    scheduler.add_job(modifications.sync_modifications, "interval", seconds=config.SYNC_INTERVAL_SECONDS)

    supabase.table("sync_status").upsert({"id": 1, "last_sync": "now()"}).execute()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
