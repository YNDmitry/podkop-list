# Podkop List - SRS Builder

Автоматическая сборка правил доменов в формат SRS (sing-box rule-set) из различных источников.

## Что это делает

Скрипт загружает списки доменов из:

- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) - основной репозиторий
- Пользовательских источников из `sources.txt`

Компилирует их в формат `.srs` для использования в [sing-box](https://github.com/SagerNet/sing-box).

## Требования

- Python 3.10+
- `sing-box` (установится автоматически в GitHub Actions)

Локально:

```bash
brew install sing-box  # macOS
apt install sing-box   # Linux
```

## Использование

### Локально

```bash
python3 build_srs.py
```

Результаты сохранятся в папку `SRS/`.

### Добавить свой источник

Добавьте строку в `sources.txt`:

```
https://example.com/domains.txt|my-domain-list
```

Формат: `URL|Имя`

### GitHub Actions

- **Ручной запуск**: кнопка "Run workflow" на вкладке Actions
- **Автоматический**: каждый день в 00:00 UTC

Результаты публикуются в релизах.

## Формат источника

Поддерживаемые типы строк:

```
domain.com                    # доменный суффикс (например, *.domain.com)
full:domain.com              # точный домен
regexp:^example\..*          # регулярное выражение
include:list-name            # включение другого списка
```
