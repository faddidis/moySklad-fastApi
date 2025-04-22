import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.utils import get_headers, log_response_details

async def upload_image(item):
    try:
        if not item.get("images") or not item["images"]["meta"]["size"] > 0:
            logger.debug(f"У элемента {item.get('id')} нет изображений")
            return None
            
        img_meta = item["images"]["rows"][0]
        url = img_meta["meta"]["downloadHref"]
        logger.info(f"Загрузка изображения из {url}")
        
        headers = get_headers()
        if not headers:
            logger.error("Не удалось получить заголовки для запроса изображения")
            return None
            
        response = httpx.get(url, headers=headers)
        log_response_details(response, url)
        
        if response.status_code != 200:
            logger.error(f"Не удалось загрузить изображение: {response.status_code}")
            return None
            
        image_data = response.content

        file_name = f"{item['id']}.jpg"
        logger.info(f"Загрузка файла {file_name} в Supabase Storage")
        
        # Добавляем обработку возможных ошибок при загрузке в Supabase
        try:
            supabase.storage.from_(config.SUPABASE_STORAGE_BUCKET).upload(
                file_name, 
                image_data, 
                {"content-type": "image/jpeg"}
            )
            image_url = f"{config.SUPABASE_URL}/storage/v1/object/public/{config.SUPABASE_STORAGE_BUCKET}/{file_name}"
            logger.info(f"Изображение успешно загружено. URL: {image_url}")
            return image_url
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла в Supabase: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения: {str(e)}")
        return None
