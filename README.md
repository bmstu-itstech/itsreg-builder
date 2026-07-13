# itsreg-builder

Интерактивный TUI (консольный интерфейс) для сборки JSON-файлов сценариев бота itsreg.

## Использование

```bash
# Установка зависимостей
make install

# Запуск (создает или загружает дефолтный script.json)
make run

# Запуск с указанием конкретного файла
make run ARGS=my_scenario.json

# Или прямой запуск через Python
python -m itsreg_builder script.json

```

Конструктор создает JSON-файл, соответствующий формату `CreateScriptRequest` в [itsreg API v3](https://itsreg.itsbmstu.ru/api/v3/swagger-ui/).
Чтобы загрузить готовый скрипт на платформу, используйте утилиту [itsreg-cli](https://github.com/bmstu-itstech/itsreg-cli).
