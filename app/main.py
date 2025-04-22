from fastapi import FastAPI
from app.api import routes
from app.core.scheduler import scheduler, start_scheduler
from app.services import categories, products, modifications
from app.core import config
from app.db.supabase_client import supabase
from app.logger import logger
import asyncio

app = FastAPI()
app.include_router(routes.router)

# Для хранения запущенных задач
running_tasks = set()

# Обертки для асинхронных функций
def run_sync_categories():
    task = asyncio.create_task(categories.sync_categories())
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)

def run_sync_products():
    task = asyncio.create_task(products.sync_products())
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)

def run_sync_modifications():
    task = asyncio.create_task(modifications.sync_modifications())
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)

@app.on_event("startup")
async def startup_event():
    logger.info("Запуск планировщика и приложения")
    start_scheduler()

    scheduler.add_job(run_sync_categories, "interval", seconds=config.SYNC_INTERVAL_SECONDS)
    scheduler.add_job(run_sync_products, "interval", seconds=config.SYNC_INTERVAL_SECONDS)
    scheduler.add_job(run_sync_modifications, "interval", seconds=config.SYNC_INTERVAL_SECONDS)

    supabase.table("sync_status").upsert({"id": 1, "last_sync": "now()"}).execute()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
