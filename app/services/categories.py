import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger

headers = {"Authorization": f"Bearer {config.MS_TOKEN}"}

async def sync_categories():
    url = f"{config.MS_BASE_URL}/entity/productfolder"
    response = httpx.get(url, headers=headers)
    data = response.json()["rows"]

    for cat in data:
        supabase.table("categories").upsert({
            "id": cat["id"],
            "name": cat["name"],
            "parent_id": cat.get("productFolder", {}).get("meta", {}).get("href", "").split("/")[-1] if cat.get("productFolder") else None
        }).execute()

    logger.info("Категории синхронизированы")

