import httpx
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image
from app.services.utils import get_headers, log_response_details

async def sync_modifications(stores: dict):
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
                        stock_json = {} # Присваиваем пустой словарь, чтобы избежать падения
                    
                    stock_resp.raise_for_status()

                    # --- ПРАВИЛЬНАЯ ЛОГИКА ОБРАБОТКИ ОСТАТКОВ (как в sync_products) ---
                    for mod_stock_row in stock_json.get("rows", []):
                        # Обрабатываем stockByStore (тип проверять не нужно, т.к. фильтр по variant)
                        for store_stock_info in mod_stock_row.get("stockByStore", []):
                            store_meta = store_stock_info.get("meta")
                            if store_meta and store_meta.get("href"):
                                store_id = store_meta["href"].split("/")[-1]
                                if store_id in stores:
                                    store_name = stores[store_id]
                                    stock_value = store_stock_info.get("stock", 0.0)
                                    stock_data[store_name] = stock_value
                                    logger.debug(f"Найден остаток для модификации {mod_id} на складе '{store_name}' (ID: {store_id}): {stock_value}")
                                else:
                                    logger.warning(f"Склад с ID {store_id} из остатков модификации {mod_id} не найден в общем списке складов.")
                            else:
                                logger.warning(f"Отсутствует 'meta' или 'href' в данных остатка по складу для модификации {mod_id}: {store_stock_info}")
                    # ------------------------------------------------------------------

                except Exception as e:
                    logger.warning(f"Ошибка при получении остатков для модификации {mod_name}: {str(e)}")

                # Логируем итоговые остатки перед сохранением
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
