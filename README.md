# itsreg-builder

Интерактивный TUI (консольный интерфейс) для сборки JSON-файлов сценариев бота itsreg.

## Использование

```bash
# Установка зависимостей
uv sync

# Запуск (создает или загружает дефолтный script.json)
uv run itsreg-builder

# Запуск с указанием конкретного файла
uv run itsreg-builder my_scenario.json
```

Конструктор создает JSON-файл, соответствующий формату `CreateScriptRequest` в [itsreg API v3](https://itsreg.itsbmstu.ru/api/v3/swagger-ui/).
Чтобы загрузить готовый скрипт на платформу, используйте утилиту [itsreg-cli](https://github.com/bmstu-itstech/itsreg-cli).
