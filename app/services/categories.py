import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.utils import get_headers, log_response_details

async def sync_categories():
    try:
        logger.info("Начинаем синхронизацию категорий")
        
        headers = get_headers()
        if not headers:
            logger.error("Не удалось получить заголовки для запроса. Синхронизация прервана.")
            return
        
        url = f"{config.MS_BASE_URL}/entity/productfolder"
        params = {
            "limit": 100
        }
        
        logger.info(f"Запрашиваем категории: {url}")
        response = httpx.get(url, headers=headers, params=params)
        log_response_details(response, url)
        
        response.raise_for_status()
        data = response.json()["rows"]
        logger.info(f"Получено {len(data)} категорий для обработки")

        for i, cat in enumerate(data):
            try:
                logger.info(f"Обработка категории {i+1}/{len(data)}: {cat.get('name', 'Без имени')}")
                
                supabase.table("categories").upsert({
                    "id": cat["id"],
                    "name": cat["name"],
                    "parent_id": cat.get("productFolder", {}).get("meta", {}).get("href", "").split("/")[-1] if cat.get("productFolder") else None
                }).execute()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке категории {cat.get('name', 'Без имени')}: {str(e)}")
                continue

        logger.info("Категории синхронизированы успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации категорий: {str(e)}")

