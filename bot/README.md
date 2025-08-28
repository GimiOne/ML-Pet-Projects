# Бот: шорт альткоина при падении BTC

Идея: при резком падении BTC у нас есть короткое «окно» (обычно до ~30 минут, а сильнейшее движение в первые ~10 минут), чтобы зайти в шорт по выбранной альте из топ-30. Этот бот автоматизирует детект падения BTC и выставляет шорт по альте.

В проекте разведены части: сбор цен (API или ручной), клиент биржи (Hyperliquid; по умолчанию «сухой» режим), и стратегия.

Новые возможности:
- Стоп‑лосс и тейк‑профит (SL/TP) для позиции
- Логи в консоль и файл (`/workspace/bot/logs/bot.log` по умолчанию)
- Отдельный CSV‑лог сделок с PnL (`/workspace/bot/logs/trades.csv`)
- На каждом тике вывод в консоль: текущая цена BTC, текущая цена выбранной альты и баланс HL

## Структура проекта
```
/workspace/bot
  ├─ prices/                # Поставщики цен
  │   ├─ base.py            # Общий интерфейс + PriceTick
  │   ├─ binance.py         # Онлайн цены (Binance public REST)
  │   └─ manual.py          # Ручной провайдер (подставляем цены)
  ├─ exchanges/
  │   └─ hl.py              # Клиент Hyperliquid (dry-run по умолчанию; REST-плейсхолдеры для реальных ордеров)
  ├─ strategy/
  │   └─ drop_and_short.py  # Стратегия: детект падения BTC → шорт альты + SL/TP
  ├─ logging_utils.py       # Настройка логирования и CSV-логгер сделок
  ├─ config.py              # Конфигурация стратегии и клиента HL (dataclasses)
  ├─ main.py                # CLI (Typer): run-live / manual-once / manual-replay
  ├─ requirements.txt       # Зависимости
  └─ README.md              # Это руководство
```

## Конфиг: где и что настраивать
Файл: `bot/config.py`

- `StrategyConfig`
  - `btc_symbol`: символ BTC у провайдера цен. По умолчанию `BTCUSDT`.
  - `alt_symbol`: символ альты, которую шортим. По умолчанию `ETHUSDT`.
  - `drop_pct_threshold`: порог падения BTC от локального максимума (в %), чтобы триггерить вход. Пример: `1.0`.
  - `lookback_seconds`: окно (сек), в котором ищется локальный максимум BTC. Пример: `300` (5 минут).
  - `entry_window_seconds`: длительность окна входа (сек) после первого триггера. Пример: `600` (10 минут).
  - `cooldown_seconds`: минимальная пауза между входами (сек). Пример: `900` (15 минут).
  - `alt_order_qty`: размер ордера по альте (в монетах/контрактах). Пример: `1.0`.
  - `leverage`: плечо (упрощённо, для dry-run). Пример: `3.0`.
  - `poll_interval_seconds`: период опроса цен (сек). В CLI задаётся флагом `--poll`.
  - `stop_loss_pct`: стоп‑лосс (%) от цены входа. Для шорта — рост цены на `stop_loss_pct`.
  - `take_profit_pct`: тейк‑профит (%) от цены входа. Для шорта — падение цены на `take_profit_pct`.
  - `verbose`: подробный вывод.

- `HLConfig`
  - `api_key`, `api_secret`: ключи Hyperliquid. В dry‑run не требуются.
  - `base_url`: базовый URL API HL (`https://api.hyperliquid.com`).
  - `dry_run`: «сухой» режим. При `True` заявки не отправляются на реальную биржу (имитация результата).

Важно: в `exchanges/hl.py` добавлены REST‑плейсхолдеры для реальной работы. Перед использованием в бою проверьте актуальную официальную документацию HL (эндпоинты, параметры, сигнатуры) и адаптируйте код.

## Где хранить ключи, сид-фразы, API‑ключи
- Никогда не храните секреты в репозитории (в коде, в `git`).
- Рекомендуемые варианты:
  - Переменные окружения (например, `HL_API_KEY`, `HL_API_SECRET`).
  - Сторонние менеджеры секретов (1Password, Bitwarden, AWS/GCP Secret Manager и т.п.).
  - `.env` (не коммитить) + загрузка через dotenv (можно добавить при интеграции реального API).

Пример подключения ключей через окружение (после адаптации клиента под реальные эндпоинты HL):
```
export HL_API_KEY=... 
export HL_API_SECRET=...
python3 -m bot.main run-live \
  --alt ETHUSDT \
  --threshold 1.0 \
  --lookback 300 \
  --qty 1 \
  --leverage 3 \
  --sl 2.0 \
  --tp 2.0 \
  --dry-run False
```

Сид‑фразы (seed) для DEX никогда не храните в коде или в незашифрованных переменных. Для централизованных бирж обычно используются API‑ключи.

## Логирование и PnL
- Консоль и файл: логгер пишет в консоль и в файл `--log-file` (по умолчанию `/workspace/bot/logs/bot.log`).
- На каждом тике в логах видны: `BTC=<цена> ALT(<символ>)=<цена> Balance={...}`.
- CSV‑лог сделок: `--trade-log` (по умолчанию `/workspace/bot/logs/trades.csv`) — фиксирует сделки (время входа/выхода, цену входа/выхода, количество, PnL, PnL%).
- PnL: для шорта рассчитывается как `-(exit - entry) * qty`, PnL% — относительно цены входа.

## Установка
В средах с ограничениями (Debian/Ubuntu) может потребоваться флаг `--break-system-packages`:
```bash
python3 -m pip install --break-system-packages -r /workspace/bot/requirements.txt
```
Или используйте виртуальное окружение (если доступно `python3-venv`):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Режимы и пошаговый запуск
### 1) Тестовый режим (ручные цены, без API)
- Одноразовый тик (передаём цены вручную, проверяем логику входа/выхода):
```bash
python3 -m bot.main manual-once \
  --btc 68000 \
  --alt 3400 \
  --alt-symbol ETHUSDT \
  --threshold 1.0 \
  --lookback 300 \
  --qty 1 \
  --leverage 3 \
  --sl 2.0 \
  --tp 2.0 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run
```
- Пошаговая симуляция (последовательности цен BTC и альты):
```bash
python3 -m bot.main manual-replay --alt-symbol ETHUSDT \
  --btc-seq 70000,69500,69000,68500,68000 \
  --alt-seq 3500,3470,3440,3410,3380 \
  --threshold 1.0 --lookback 300 --qty 1 --leverage 3 \
  --sl 2.0 --tp 2.0 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run
```
Ожидаемо, когда падение BTC от локального максимума превысит порог, стратегия попытается поставить шорт по альте (в dry‑run вернётся фиктивный `order_id`). При достижении SL/TP — позиция закроется, сделка запишется в CSV.

### 2) «Живой» тест (онлайн‑цены Binance, без реальных ордеров)
- Старт с опросом цен и dry‑run ордерами:
```bash
python3 -m bot.main run-live \
  --alt ETHUSDT \
  --threshold 1.0 \
  --lookback 300 \
  --qty 1 \
  --leverage 3 \
  --sl 2.0 \
  --tp 2.0 \
  --poll 2 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run
```
Стратегия будет опрашивать public REST Binance, печатать цены и баланс HL (в dry‑run — фиктивный), входить по условиям, сопровождать SL/TP, писать логи и CSV‑сделки.

### 3) Боевой режим (реальные ордера HL)
- В `exchanges/hl.py` добавлены REST‑плейсхолдеры. Перед использованием обязательно:
  1. Сверьте и адаптируйте эндпоинты/параметры/сигнатуры по официальной документации HL.
  2. Настройте ключи и секреты через окружение (или менеджер секретов) и пробросьте их в `HLConfig`.
  3. Запускайте с `--dry-run False` только после тестирования. Добавьте полноценный риск‑менеджмент.

Пример запуска (после адаптации клиента и установки ключей):
```bash
export HL_API_KEY=...
export HL_API_SECRET=...
python3 -m bot.main run-live \
  --alt ETHUSDT \
  --threshold 1.0 \
  --lookback 300 \
  --qty 1 \
  --leverage 3 \
  --sl 2.0 \
  --tp 2.0 \
  --poll 2 \
  --dry-run False
```

## CLI: команды и флаги
Общий хелп:
```bash
python3 -m bot.main --help
```

### Команда: run-live — Работа с онлайн‑ценами (Binance)
- `--alt` (str): символ альты, например `ETHUSDT`.
- `--threshold` (float): порог падения BTC от локального максимума (%) для входа.
- `--lookback` (int, сек): окно поиска локального максимума BTC.
- `--qty` (float): размер ордера по альте (монеты/контракты).
- `--leverage` (float): плечо (для расчёта/логики dry‑run).
- `--poll` (float, сек): период опроса цен.
- `--sl` (float, %): стоп‑лосс от цены входа.
- `--tp` (float, %): тейк‑профит от цены входа.
- `--log-file` (str): путь к файлу логов (по умолчанию `/workspace/bot/logs/bot.log`).
- `--trade-log` (str): путь к CSV‑логу сделок (по умолчанию `/workspace/bot/logs/trades.csv`).
- `--dry-run` (bool): сухой режим клиента HL (по умолчанию `True`).
- `--verbose` (bool): подробный вывод диагностики.

Пример:
```bash
python3 -m bot.main run-live --alt AVAXUSDT --threshold 1.2 --lookback 300 \
  --qty 2 --leverage 3 --poll 2 --sl 2.0 --tp 2.5 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run --verbose
```

### Команда: manual-once — Одноразовый шаг стратегии (ручные цены)
- `--btc` (float): BTC цена.
- `--alt` (float): ALT цена.
- `--alt-symbol` (str): символ альты.
- `--threshold` (float): порог падения BTC от локального максимума (%).
- `--lookback` (int, сек): окно для локального максимума BTC.
- `--qty` (float): размер ордера по альте.
- `--leverage` (float): плечо (для dry‑run).
- `--sl` (float, %): стоп‑лосс.
- `--tp` (float, %): тейк‑профит.
- `--log-file` (str): файл логов.
- `--trade-log` (str): CSV‑лог сделок.
- `--dry-run` (bool): сухой режим HL.
- `--verbose` (bool): подробный вывод.

Пример:
```bash
python3 -m bot.main manual-once --btc 70000 --alt 3500 --alt-symbol ETHUSDT \
  --threshold 1.0 --lookback 300 --qty 1 --leverage 3 \
  --sl 1.5 --tp 2.5 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run --verbose
```

### Команда: manual-replay — Пошаговая симуляция (ручные цены)
- `--btc-seq` (CSV float): последовательность цен BTC, через запятую.
- `--alt-seq` (CSV float): последовательность цен альты, через запятую.
- `--alt-symbol` (str): символ альты.
- `--threshold` (float): порог падения BTC от локального максимума (%).
- `--lookback` (int, сек): окно для локального максимума BTC.
- `--qty` (float): размер ордера по альте.
- `--leverage` (float): плечо (для dry‑run).
- `--sl` (float, %): стоп‑лосс.
- `--tp` (float, %): тейк‑профит.
- `--log-file` (str): файл логов.
- `--trade-log` (str): CSV‑лог сделок.
- `--dry-run` (bool): сухой режим HL.
- `--verbose` (bool): подробный вывод.
- `--step-delay` (float, сек): задержка между «тиками».

Пример:
```bash
python3 -m bot.main manual-replay --alt-symbol SUIUSDT \
  --btc-seq 70000,69300,68900,68800 \
  --alt-seq  140,   138,   133,   132 \
  --threshold 1.0 --lookback 300 --qty 10 --leverage 3 \
  --sl 2.0 --tp 2.0 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --dry-run --verbose --step-delay 0
```

## Логика стратегии (вкратце)
- Поддерживается история цен BTC в окне `lookback_seconds`.
- На каждом тике считается падение от локального максимума в этом окне. Если падение ≥ `drop_pct_threshold`, помечается время первого триггера и активируется «окно входа» (`entry_window_seconds`).
- Если мы находимся в окне входа, нет `cooldown`, и падение подтверждено, выставляется шорт по выбранной альте. Для открытой позиции сопровождаются SL/TP; при срабатывании — позиция закрывается и сделка пишется в CSV.

## Безопасность, ограничения и дальнейшие шаги
- Пример учебный: сетевые ошибки/ретраи/лимиты/персистентность/аудит/алерты не реализованы.
- Для продакшна обязательно добавить:
  - Полноценный клиент HL (REST/WS, подписи, проверка балансов/маржи, расчёт размера позиции, лимиты).
  - Риск‑менеджмент (стоп‑лосс/тейк‑профит/макс. дневной убыток/ограничение размера позиции и частоты входов).
  - Обработку сетевых ошибок (ретраи, бэкофф, таймауты), мониторинг и алерты.
  - Персистентность (состояния, сделки, журналы, аудит, повторный запуск без потери контекста).
  - Надёжное управление секретами.

## Быстрый старт
```bash
# Установка зависимостей (вариант без venv)
python3 -m pip install --break-system-packages -r /workspace/bot/requirements.txt

# Хелп по CLI
python3 -m bot.main --help

# Минимальный dry‑run с онлайн ценами
python3 -m bot.main run-live --alt ETHUSDT --threshold 1.0 --lookback 300 --qty 1 \
  --leverage 3 --sl 2.0 --tp 2.0 --dry-run

# Минимальный ручной тест
python3 -m bot.main manual-once --btc 70000 --alt 3500 --alt-symbol ETHUSDT \
  --threshold 1.0 --lookback 300 --qty 1 --leverage 3 --sl 2.0 --tp 2.0 --dry-run
```