from fastapi import FastAPI
from app.api import routes
from app.core.scheduler import scheduler, start_scheduler
from app.services import categories, products, modifications
from app.core import config
from app.db.supabase_client import supabase
from app.logger import logger
import asyncio
import time
from datetime import datetime, timedelta

app = FastAPI()
app.include_router(routes.router)

# Обертки для асинхронных функций
def run_sync_categories():
    # Создаем новый цикл событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Запускаем асинхронную функцию в этом цикле
        loop.run_until_complete(categories.sync_categories())
    except Exception as e:
        logger.error(f"Ошибка в планировщике категорий: {str(e)}")
    finally:
        # Закрываем цикл событий
        loop.close()

def run_sync_products():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(products.sync_products())
    except Exception as e:
        logger.error(f"Ошибка в планировщике товаров: {str(e)}")
    finally:
        loop.close()

def run_sync_modifications():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(modifications.sync_modifications())
    except Exception as e:
        logger.error(f"Ошибка в планировщике модификаций: {str(e)}")
    finally:
        loop.close()

def run_full_sync():
    """Запускаем полную синхронизацию последовательно"""
    logger.info("Запуск полной синхронизации")
    run_sync_categories()
    # Пауза между синхронизациями для предотвращения конфликтов
    time.sleep(2)
    run_sync_products()
    time.sleep(2)
    run_sync_modifications()
    logger.info("Полная синхронизация завершена")

@app.on_event("startup")
async def startup_event():
    logger.info("Запуск планировщика и приложения")
    start_scheduler()

    # Сначала синхронизируем категории
    scheduler.add_job(run_sync_categories, "interval", seconds=config.SYNC_INTERVAL_SECONDS, id="categories_sync")
    
    # Затем запускаем синхронизацию товаров с задержкой в 10 секунд
    scheduler.add_job(run_sync_products, "interval", seconds=config.SYNC_INTERVAL_SECONDS, 
                     start_date=datetime.now() + timedelta(seconds=10), id="products_sync")
    
    # Затем запускаем синхронизацию модификаций с задержкой в 20 секунд
    scheduler.add_job(run_sync_modifications, "interval", seconds=config.SYNC_INTERVAL_SECONDS,
                     start_date=datetime.now() + timedelta(seconds=20), id="modifications_sync")
    
    # Запускаем немедленную полную синхронизацию через 3 секунды после старта
    scheduler.add_job(run_full_sync, trigger='date', 
                     run_date=datetime.now() + timedelta(seconds=3), 
                     id="initial_sync")

    supabase.table("sync_status").upsert({"id": 1, "last_sync": "now()"}).execute()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
