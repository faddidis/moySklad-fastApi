📦 MoySklad FastAPI Sync
Сервис для синхронизации данных из МойСклад в Supabase:
категории товаров (с родителями)
товары (с ценами и изображениями)
модификации товаров (с характеристиками, остатками по складам)
склады
загрузка изображений в Supabase Storage

📁 Структура проекта

moySklad-fastApi/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── services/
│   ├── logger.py
│   └── main.py
├── sql/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md

🚀 Как запустить

1️⃣ Клонируй проект
git clone https://github.com/faddidis/moySklad-fastApi.git
cd moySklad-fastApi

2️⃣ Настрой .env
Скопируй .env.example → .env и заполни своими данными:
cp .env.example .env

Впиши:
SUPABASE_URL
SUPABASE_KEY (сервисный ключ)
SUPABASE_STORAGE_BUCKET
MS_BASE_URL
MS_TOKEN
SYNC_INTERVAL_SECONDS

3️⃣ Применить SQL для Supabase
Скопируй содержимое sql/supabase_schema.sql в свой Supabase SQL Editor и выполни.

4️⃣ Запуск через Docker
docker-compose up --build
API будет доступно на http://localhost:8000/docs

📖 Возможности

🔄 Периодическая синхронизация по интервалу из .env

📁 Загрузка изображений товаров/модификаций в Supabase Storage

📊 Остатки по складам в модификациях

💰 Множественные цены (оптовая, розничная и др.)

✅ Healthcheck: /health

📃 Логирование в logs/app.log

🐳 Полезные команды
Остановить контейнеры:

docker-compose down
Пересобрать и перезапустить:
docker-compose up --build
📌 Автор
faddidis 👌

