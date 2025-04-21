import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image

headers = {"Authorization": f"Bearer {config.MS_TOKEN}"}

async def sync_modifications():
    url = f"{config.MS_BASE_URL}/entity/variant"
    response = httpx.get(url, headers=headers)
    data = response.json()["rows"]

    for mod in data:
        stock_url = f"{config.MS_BASE_URL}/report/stock/bystore?filter=variant=https://api.moysklad.ru/api/remap/1.2/entity/variant/{mod['id']}"
        stock_resp = httpx.get(stock_url, headers=headers)
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

    logger.info("Модификации синхронизированы")
