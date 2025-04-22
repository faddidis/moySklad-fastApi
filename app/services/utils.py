import base64
from app.core import config
from app.logger import logger

# Создаем заголовки для API МойСклад
def get_headers():
    # Проверяем, что токен не пустой
    if not config.MS_TOKEN:
        logger.error("МойСклад токен отсутствует! Проверьте .env файл.")
        return None
        
    # Логируем для отладки
    logger.debug(f"Используем токен: {config.MS_TOKEN[:5]}...")
    
    # Более полный набор заголовков
    headers = {
        "Authorization": f"Bearer {config.MS_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "MoySklad-FastAPI-Sync/1.0"
    }
    
    return headers

# Утилита для проверки ответа API
def log_response_details(response, url):
    logger.info(f"URL запроса: {url}")
    logger.info(f"Метод запроса: {response.request.method}")
    logger.info(f"Заголовки запроса: {response.request.headers}")
    logger.info(f"Статус ответа: {response.status_code}")
    logger.info(f"Заголовки ответа: {response.headers}")
    if response.status_code >= 400:
        logger.error(f"Тело ответа: {response.text}") 