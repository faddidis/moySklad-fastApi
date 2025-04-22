import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image

headers = {"Authorization": f"Bearer {config.MS_TOKEN}"}

async def sync_products():
    try:
        logger.info("Начинаем синхронизацию товаров")
        
        # Получаем типы цен
        prices_url = f"{config.MS_BASE_URL}/entity/priceType"
        logger.info(f"Запрашиваем типы цен: {prices_url}")
        price_response = httpx.get(prices_url, headers=headers)
        price_response.raise_for_status()
        price_types = {p["id"]: p["name"] for p in price_response.json()["rows"]}
        logger.info(f"Получено {len(price_types)} типов цен")

        # Получаем склады как словарь
        stores_url = f"{config.MS_BASE_URL}/entity/store"
        logger.info(f"Запрашиваем склады: {stores_url}")
        store_response = httpx.get(stores_url, headers=headers)
        store_response.raise_for_status()
        stores = {s["id"]: s["name"] for s in store_response.json()["rows"]}
        logger.info(f"Получено {len(stores)} складов")

        url = f"{config.MS_BASE_URL}/entity/product"
        logger.info(f"Запрашиваем товары: {url}")
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()["rows"]
        logger.info(f"Получено {len(data)} товаров для обработки")

        for i, product in enumerate(data):
            try:
                logger.info(f"Обработка товара {i+1}/{len(data)}: {product.get('name', 'Без имени')}")
                
                # Получаем цены
                prices = {price_types[p["priceType"]["meta"]["href"].split("/")[-1]]: p["value"] / 100 for p in product.get("salePrices", [])}

                # Картинка
                image_url = await upload_image(product)
                
                # Получаем остатки по складам
                product_id = product['id']
                stock_url = f"{config.MS_BASE_URL}/report/stock/bystore?filter=product=https://api.moysklad.ru/api/remap/1.2/entity/product/{product_id}"
                logger.info(f"Запрашиваем остатки для товара {product_id}")
                stock_resp = httpx.get(stock_url, headers=headers)
                stock_resp.raise_for_status()
                stock_data = {
                    stores[item["stockStore"]["meta"]["href"].split("/")[-1]]: item["stock"]
                    for item in stock_resp.json().get("rows", [])
                }

                supabase.table("products").upsert({
                    "id": product["id"],
                    "name": product["name"],
                    "description": product.get("description"),
                    "image_url": image_url,
                    "category_id": product.get("productFolder", {}).get("meta", {}).get("href", "").split("/")[-1] if product.get("productFolder") else None,
                    "prices": prices,
                    "stock": stock_data
                }).execute()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке товара {product.get('name', 'Без имени')}: {str(e)}")
                continue

        logger.info("Товары синхронизированы успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации товаров: {str(e)}")
