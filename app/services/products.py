import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image

headers = {"Authorization": f"Bearer {config.MS_TOKEN}"}

async def sync_products():
    # Получаем типы цен
    prices_url = f"{config.MS_BASE_URL}/entity/priceType"
    price_response = httpx.get(prices_url, headers=headers)
    price_types = {p["id"]: p["name"] for p in price_response.json()["rows"]}

    # Получаем склады
    stores_url = f"{config.MS_BASE_URL}/entity/store"
    store_response = httpx.get(stores_url, headers=headers)
    stores = {s["id"]: s["name"] for s in store_response.json()["rows"]}

    for store_id, store_name in stores.items():
        supabase.table("stores").upsert({
            "id": store_id,
            "name": store_name
        }).execute()

    url = f"{config.MS_BASE_URL}/entity/product"
    response = httpx.get(url, headers=headers)
    data = response.json()["rows"]

    for product in data:
        # Получаем цены
        prices = {price_types[p["priceType"]["meta"]["href"].split("/")[-1]]: p["value"] / 100 for p in product.get("salePrices", [])}

        # Картинка
        image_url = await upload_image(product)

        supabase.table("products").upsert({
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description"),
            "image_url": image_url,
            "category_id": product.get("productFolder", {}).get("meta", {}).get("href", "").split("/")[-1] if product.get("productFolder") else None,
            "prices": prices
        }).execute()

    logger.info("Товары синхронизированы")
