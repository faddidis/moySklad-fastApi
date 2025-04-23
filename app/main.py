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
import httpx
from app.services.utils import get_headers, log_response_details

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

def run_sync_products(stores: dict):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(products.sync_products(stores))
    except Exception as e:
        logger.error(f"Ошибка в планировщике товаров: {str(e)}")
    finally:
        loop.close()

def run_sync_modifications(stores: dict):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(modifications.sync_modifications(stores))
    except Exception as e:
        logger.error(f"Ошибка в планировщике модификаций: {str(e)}")
    finally:
        loop.close()

def run_full_sync():
    """Запускаем полную синхронизацию последовательно"""
    logger.info("Запуск полной синхронизации")
    
    # Загружаем склады один раз
    stores = {}
    try:
        headers = get_headers()
        if headers:
            stores_url = f"{config.MS_BASE_URL}/entity/store"
            logger.info(f"[Full Sync] Запрашиваем склады: {stores_url}")
            store_response = httpx.get(stores_url, headers=headers)
            log_response_details(store_response, stores_url)
            store_response.raise_for_status()
            stores = {s["id"]: s["name"] for s in store_response.json()["rows"]}
            logger.info(f"[Full Sync] Получено {len(stores)} складов")
        else:
            logger.error("[Full Sync] Не удалось получить заголовки для запроса складов.")
    except Exception as e:
        logger.error(f"[Full Sync] Ошибка при загрузке складов: {str(e)}")
        # TODO: Решить, стоит ли продолжать без складов или прервать
        # Пока что продолжаем, но остатки не будут правильно обработаны

    # Запускаем синхронизацию категорий (склады не нужны)
    run_sync_categories()
    time.sleep(2)
    
    # Передаем загруженные склады в синхронизацию товаров и модификаций
    run_sync_products(stores)
    time.sleep(2)
    run_sync_modifications(stores)
    
    logger.info("Полная синхронизация завершена")

@app.on_event("startup")
async def startup_event():
    logger.info("Запуск планировщика и приложения")
    start_scheduler()

    # Запускаем немедленную полную синхронизацию через 3 секунды после старта
    # Эта функция теперь загрузит склады и передаст их дальше
    scheduler.add_job(run_full_sync, trigger='date', 
                     run_date=datetime.now() + timedelta(seconds=3), 
                     id="initial_sync")

    # --- Планирование интервальной синхронизации --- 
    # ПРИМЕЧАНИЕ: Интервальная синхронизация теперь будет сложнее,
    # т.к. нужно передавать актуальные склады.
    # Пока что оставим старую логику для интервалов, но она не будет 
    # корректно работать с остатками, если склады изменятся.
    # TODO: Переделать интервальную синхронизацию для передачи складов.
    
    # Сначала синхронизируем категории
    scheduler.add_job(run_sync_categories, "interval", seconds=config.SYNC_INTERVAL_SECONDS, id="categories_sync")
    
    # Создаем обертки для интервальных задач БЕЗ передачи складов (временно)
    def run_interval_sync_products():
        run_sync_products({}) # Передаем пустой словарь
        
    def run_interval_sync_modifications():
        run_sync_modifications({}) # Передаем пустой словарь

    # Затем запускаем синхронизацию товаров с задержкой (ВРЕМЕННО ОТКЛЮЧЕНО)
    # scheduler.add_job(run_interval_sync_products, "interval", seconds=config.SYNC_INTERVAL_SECONDS, 
    #                  start_date=datetime.now() + timedelta(seconds=10), id="products_sync")
    
    # Затем запускаем синхронизацию модификаций с задержкой (ВРЕМЕННО ОТКЛЮЧЕНО)
    # scheduler.add_job(run_interval_sync_modifications, "interval", seconds=config.SYNC_INTERVAL_SECONDS,
    #                  start_date=datetime.now() + timedelta(seconds=20), id="modifications_sync")

    supabase.table("sync_status").upsert({"id": 1, "last_sync": "now()"}).execute()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
