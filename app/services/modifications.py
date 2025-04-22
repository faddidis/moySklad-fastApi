import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image

headers = {"Authorization": f"Bearer {config.MS_TOKEN}"}

async def sync_modifications():
    try:
        logger.info("Начинаем синхронизацию модификаций")
        
        url = f"{config.MS_BASE_URL}/entity/variant"
        logger.info(f"Запрашиваем модификации: {url}")
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()["rows"]
        logger.info(f"Получено {len(data)} модификаций для обработки")

        for i, mod in enumerate(data):
            try:
                logger.info(f"Обработка модификации {i+1}/{len(data)}: {mod.get('name', 'Без имени')}")
                
                mod_id = mod['id']
                stock_url = f"{config.MS_BASE_URL}/report/stock/bystore?filter=variant=https://api.moysklad.ru/api/remap/1.2/entity/variant/{mod_id}"
                logger.info(f"Запрашиваем остатки для модификации {mod_id}")
                stock_resp = httpx.get(stock_url, headers=headers)
                stock_resp.raise_for_status()
                stock_data = {
                    item["stockStore"]["name"]: item["stock"]
                    for item in stock_resp.json().get("rows", [])
                }

                prices = {p["priceType"]["meta"]["href"].split("/")[-1]: p["value"] / 100 for p in mod.get("salePrices", [])}

                image_url = await upload_image(mod)

                supabase.table("modifications").upsert({
                    "id": mod["id"],
                    "product_id": mod["product"]["meta"]["href"].split("/")[-1],
                    "name": mod["name"],
                    "characteristics": mod.get("characteristics"),
                    "image_url": image_url,
                    "prices": prices,
                    "stock": stock_data
                }).execute()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке модификации {mod.get('name', 'Без имени')}: {str(e)}")
                continue

        logger.info("Модификации синхронизированы успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации модификаций: {str(e)}")
