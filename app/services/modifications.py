import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image
from app.services.utils import get_headers, log_response_details

async def sync_modifications():
    try:
        logger.info("Начинаем синхронизацию модификаций")
        
        headers = get_headers()
        if not headers:
            logger.error("Не удалось получить заголовки для запроса. Синхронизация прервана.")
            return
        
        # Используем полный URL с указанием API версии
        url = f"{config.MS_BASE_URL}/entity/variant"
        logger.info(f"Запрашиваем модификации: {url}")
        
        # Добавляем параметры запроса для пагинации и ограничения количества
        params = {
            "limit": 100
        }
        
        response = httpx.get(url, headers=headers, params=params)
        log_response_details(response, url)
        
        response.raise_for_status()
        data = response.json()["rows"]
        logger.info(f"Получено {len(data)} модификаций для обработки")

        for i, mod in enumerate(data):
            try:
                # Получаем основную информацию о модификации
                mod_name = mod.get('name', 'Без имени')
                mod_id = mod.get('id', 'unknown')
                logger.info(f"Обработка модификации {i+1}/{len(data)}: {mod_name} (ID: {mod_id})")
                
                # Проверяем существование товара в базе данных перед добавлением модификации
                product_id = None
                if "product" in mod and "meta" in mod["product"] and "href" in mod["product"]["meta"]:
                    product_id = mod["product"]["meta"]["href"].split("/")[-1]
                else:
                    logger.warning(f"Модификация {mod_name} не содержит ссылки на товар. Пропускаем.")
                    continue
                
                # Проверка существования товара в базе
                product_exists = supabase.table("products").select("id").eq("id", product_id).execute()
                
                if not product_exists.data:
                    logger.warning(f"Товар с ID {product_id} не найден в базе данных. Пропускаем модификацию {mod_name}.")
                    continue
                
                # Получаем остатки по складам
                stock_data = {}
                try:
                    stock_url = f"{config.MS_BASE_URL}/report/stock/bystore?filter=variant=https://api.moysklad.ru/api/remap/1.2/entity/variant/{mod_id}"
                    logger.info(f"Запрашиваем остатки для модификации {mod_id}")
                    stock_resp = httpx.get(stock_url, headers=headers)
                    log_response_details(stock_resp, stock_url)
                    
                    # Log the stock response JSON for debugging
                    stock_json = None
                    try:
                        stock_json = stock_resp.json()
                        logger.debug(f"JSON ответа для остатков модификации {mod_id}: {stock_json}")
                    except Exception as json_e:
                        logger.error(f"Ошибка парсинга JSON остатков модификации {mod_id}: {json_e}")
                        logger.error(f"Тело ответа (текст): {stock_resp.text}")
                        stock_json = {} # Assign empty dict to avoid breaking flow
                    
                    stock_resp.raise_for_status()
                    
                    # Исправляем ошибку с stockStore - Process stock data
                    for item in stock_json.get("rows", []): # Assuming "rows" key exists
                        if "stockStore" in item and "name" in item["stockStore"]:
                            stock_data[item["stockStore"]["name"]] = item["stock"]
                        else:
                             logger.warning(f"Отсутствует 'stockStore' или 'name' в данных остатка для модификации {mod_id}: {item}")
                except Exception as e:
                    logger.warning(f"Ошибка при получении остатков для модификации {mod_name}: {str(e)}")

                # Log final stock data before upsert
                logger.debug(f"Итоговые остатки для модификации {mod_id} перед сохранением: {stock_data}")

                # Получаем цены
                prices = {}
                if "salePrices" in mod and mod["salePrices"]:
                    for p in mod.get("salePrices", []):
                        try:
                            price_type_href = p.get("priceType", {}).get("meta", {}).get("href")
                            if price_type_href:
                                price_type_id = price_type_href.split("/")[-1]
                                prices[price_type_id] = p["value"] / 100
                        except Exception as e:
                            logger.warning(f"Ошибка при обработке цены модификации {mod_name}: {str(e)}")

                # Загружаем изображение если оно есть
                image_url = None
                try:
                    # Эта функция уже обрабатывает случай отсутствия изображений
                    image_url = await upload_image(mod)
                    if image_url:
                        logger.info(f"Изображение для модификации {mod_name} успешно загружено")
                    else:
                        logger.info(f"Для модификации {mod_name} нет изображения или не удалось загрузить")
                except Exception as e:
                    logger.warning(f"Ошибка при загрузке изображения модификации {mod_name}: {str(e)}")

                # Сохраняем в Supabase
                characteristics = mod.get("characteristics", [])
                
                supabase.table("modifications").upsert({
                    "id": mod_id,
                    "product_id": product_id,
                    "name": mod_name,
                    "characteristics": characteristics,
                    "image_url": image_url,
                    "prices": prices,
                    "stock": stock_data
                }).execute()
                
                logger.info(f"Модификация {mod_name} успешно сохранена в базе")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке модификации {mod.get('name', 'Без имени')}: {str(e)}")
                continue

        logger.info("Модификации синхронизированы успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации модификаций: {str(e)}")
