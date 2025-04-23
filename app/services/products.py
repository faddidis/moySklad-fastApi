import httpx
import base64
from app.db.supabase_client import supabase
from app.core import config
from app.logger import logger
from app.services.storage import upload_image
from app.services.utils import get_headers, log_response_details

async def sync_products(stores: dict):
    try:
        logger.info("Начинаем синхронизацию товаров")
        
        headers = get_headers()
        if not headers:
            logger.error("Не удалось получить заголовки для запроса. Синхронизация прервана.")
            return
        
        # Получаем типы цен
        prices_url = f"{config.MS_BASE_URL}/context/companysettings/pricetype"
        logger.info(f"Запрашиваем типы цен: {prices_url}")
        
        # Делаем запрос с новыми заголовками
        price_response = httpx.get(prices_url, headers=headers)
        log_response_details(price_response, prices_url)
        
        # Log the parsed JSON response for debugging
        parsed_json = None # Initialize parsed_json
        try:
            parsed_json = price_response.json()
            logger.debug(f"Получен JSON ответа для типов цен: {parsed_json}") 
        except Exception as json_e:
            logger.error(f"Ошибка парсинга JSON для типов цен: {json_e}")
            logger.error(f"Тело ответа (текст): {price_response.text}")
            raise # Re-raise the exception to be caught by the main handler

        price_response.raise_for_status() # Проверяем статус после парсинга
        # API возвращает список напрямую, а не словарь с ключом "rows"
        price_types = {p["id"]: p["name"] for p in parsed_json} 
        logger.info(f"Получено {len(price_types)} типов цен")

        # Добавляем параметры для запроса товаров
        url = f"{config.MS_BASE_URL}/entity/product"
        params = {
            "limit": 100
        }
        
        logger.info(f"Запрашиваем товары: {url}")
        response = httpx.get(url, headers=headers, params=params)
        log_response_details(response, url)
        
        response.raise_for_status()
        data = response.json()["rows"]
        logger.info(f"Получено {len(data)} товаров для обработки")

        for i, product in enumerate(data):
            try:
                product_name = product.get('name', 'Без имени')
                product_id = product.get('id', 'unknown')
                logger.info(f"Обработка товара {i+1}/{len(data)}: {product_name} (ID: {product_id})")
                
                # Получаем цены
                prices = {}
                if "salePrices" in product and product["salePrices"]:
                    for p in product["salePrices"]:
                        try:
                            price_type_href = p.get("priceType", {}).get("meta", {}).get("href")
                            if price_type_href:
                                price_type_id = price_type_href.split("/")[-1]
                                if price_type_id in price_types:
                                    prices[price_types[price_type_id]] = p["value"] / 100
                        except Exception as e:
                            logger.warning(f"Ошибка при обработке цены товара {product_name}: {str(e)}")

                # Загружаем изображение если оно есть
                image_url = None
                try:
                    # Эта функция уже обрабатывает случай отсутствия изображений
                    image_url = await upload_image(product)
                    if image_url:
                        logger.info(f"Изображение для товара {product_name} успешно загружено")
                    else:
                        logger.info(f"Для товара {product_name} нет изображения или не удалось загрузить")
                except Exception as e:
                    logger.warning(f"Ошибка при загрузке изображения товара {product_name}: {str(e)}")
                
                # Получаем остатки по складам
                stock_data = {}
                try:
                    stock_url = f"{config.MS_BASE_URL}/report/stock/bystore?filter=product=https://api.moysklad.ru/api/remap/1.2/entity/product/{product_id}"
                    logger.info(f"Запрашиваем остатки для товара {product_id}")
                    stock_resp = httpx.get(stock_url, headers=headers)
                    log_response_details(stock_resp, stock_url)
                    
                    # Log the stock response JSON for debugging
                    stock_json = None
                    try:
                        stock_json = stock_resp.json()
                        logger.debug(f"JSON ответа для остатков товара {product_id}: {stock_json}")
                    except Exception as json_e:
                        logger.error(f"Ошибка парсинга JSON остатков товара {product_id}: {json_e}")
                        logger.error(f"Тело ответа (текст): {stock_resp.text}")
                        stock_json = {} # Присваиваем пустой словарь, чтобы избежать падения, если парсинг не удался, но статус OK
                    
                    stock_resp.raise_for_status()
                    
                    # Обработка данных об остатках
                    for product_stock_row in stock_json.get("rows", []): # Предполагаем, что ключ "rows" существует
                        # --- ДОБАВЛЕНА ПРОВЕРКА ТИПА --- 
                        # Обрабатываем только строку, относящуюся непосредственно к товару,
                        # игнорируем строки модификаций, которые API может вернуть здесь же.
                        if product_stock_row.get("meta", {}).get("type") == "product":
                            for store_stock_info in product_stock_row.get("stockByStore", []):
                                store_meta = store_stock_info.get("meta")
                                if store_meta and store_meta.get("href"):
                                    store_id = store_meta["href"].split("/")[-1]
                                    if store_id in stores:
                                        store_name = stores[store_id]
                                        stock_value = store_stock_info.get("stock", 0.0) # Получаем остаток
                                        stock_data[store_name] = stock_value
                                        logger.debug(f"Найден остаток для товара {product_id} на складе '{store_name}' (ID: {store_id}): {stock_value}")
                                    else:
                                        logger.warning(f"Склад с ID {store_id} из остатков товара {product_id} не найден в общем списке складов.")
                                else:
                                    logger.warning(f"Отсутствует 'meta' или 'href' в данных остатка по складу для товара {product_id}: {store_stock_info}")
                        # --------------------------------
                        else:
                            logger.debug(f"Пропущена строка с типом '{product_stock_row.get('meta', {}).get('type')}' при обработке остатков товара {product_id}")
                    # --------------------------------------------------

                except Exception as e:
                    logger.warning(f"Ошибка при получении остатков товара {product_name}: {str(e)}")
                
                # Логируем итоговые остатки перед сохранением
                logger.debug(f"Итоговые остатки для товара {product_id} перед сохранением: {stock_data}")

                # Определяем ID категории, если она есть
                category_id = None
                if product.get("productFolder") and product["productFolder"].get("meta") and product["productFolder"]["meta"].get("href"):
                    category_id = product["productFolder"]["meta"]["href"].split("/")[-1]

                # Сохраняем товар в Supabase
                supabase.table("products").upsert({
                    "id": product_id,
                    "name": product_name,
                    "description": product.get("description"),
                    "image_url": image_url,
                    "category_id": category_id,
                    "prices": prices,
                    "stock": stock_data
                }).execute()
                
                logger.info(f"Товар {product_name} успешно сохранен в базе")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке товара {product.get('name', 'Без имени')}: {str(e)}")
                continue

        logger.info("Товары синхронизированы успешно")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации товаров: {str(e)}")
