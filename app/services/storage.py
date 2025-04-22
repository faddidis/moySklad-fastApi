import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.services.utils import get_headers

async def upload_image(item):
    if "images" in item and item["images"]["meta"]["size"] > 0:
        img_meta = item["images"]["rows"][0]
        url = img_meta["meta"]["downloadHref"]
        headers = get_headers()
        image_data = httpx.get(url, headers=headers).content

        file_name = f"{item['id']}.jpg"
        supabase.storage.from_(config.SUPABASE_STORAGE_BUCKET).upload(file_name, image_data, {"content-type": "image/jpeg"})

        return f"{config.SUPABASE_URL}/storage/v1/object/public/{config.SUPABASE_STORAGE_BUCKET}/{file_name}"
    return None
