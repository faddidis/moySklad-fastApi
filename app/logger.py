from loguru import logger

logger.add("logs/app.log", rotation="1 day", retention="7 days")
