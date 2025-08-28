# Бот: шорт альткоина при падении BTC

Идея: при резком падении BTC у нас есть короткое «окно» (обычно до ~30 минут, а сильнейшее движение в первые ~10 минут), чтобы зайти в шорт по выбранной альте из топ-30. Этот бот автоматизирует детект падения BTC и выставляет шорт по альте.

В проекте разведены части: сбор цен (API или ручной), клиент биржи (Hyperliquid; по умолчанию «сухой» режим), и стратегия.

Новые возможности:
- Стоп‑лосс и тейк‑профит (SL/TP) для позиции
- Логи в консоль и файл (`/workspace/bot/logs/bot.log` по умолчанию)
- Отдельный CSV‑лог сделок с PnL (`/workspace/bot/logs/trades.csv`)
- На каждом тике вывод в консоль: текущая цена BTC, текущая цена выбранной альты и баланс HL
- Мгновенная команда CLI для открытия шорта без стратегии: `short`
- Симуляция падения BTC с реальным входом при достижении порога: `simulate_btc_fall`

## Структура проекта
```
/workspace/bot
  ├─ prices/                # Поставщики цен
  │   ├─ base.py            # Общий интерфейс + PriceTick
  │   ├─ binance.py         # Онлайн цены (Binance public REST)
  │   ├─ hl_info.py         # Цены с HL Info (мейннет/тестнет)
  │   └─ manual.py          # Ручной провайдер (подставляем цены)
  ├─ exchanges/
  │   └─ hl.py              # Клиент Hyperliquid SDK (order/trigger, cross/isolated, округления)
  ├─ strategy/
  │   └─ drop_and_short.py  # Стратегия: детект падения BTC → шорт альты + SL/TP
  ├─ logging_utils.py       # Настройка логирования и CSV-логгер сделок
  ├─ config.py              # Конфигурация стратегии и клиента HL (dataclasses)
  ├─ main.py                # CLI (Typer): run-live / manual-once / manual-replay / short / simulate_btc_fall
  ├─ scripts/
  │   └─ hl_short_test.py   # Автономный тест постановки шорта на HL (SDK)
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

### 3) Мгновенный шорт без стратегии (CLI `short`)
Открывает рыночный шорт выбранной альты и сопровождает его SL/TP.

Флаги:
- `--alt-symbol` (str): символ альты (например, `ETHUSDT`).
- `--qty` (float): размер позиции (монеты), используется если не задан `--usd-notional`.
- `--usd-notional` (float): размер позиции в USD; перекрывает `--qty`.
- `--leverage` (int): плечо для установки режима маржи на HL.
- `--isolated` (bool): изолированная маржа (по умолчанию cross).
- `--sl` (float, %): стоп‑лосс относительно цены входа.
- `--tp` (float, %): тейк‑профит относительно цены входа.
- `--sl-price` (float): стоп‑лосс абсолютной ценой.
- `--tp-price` (float): тейк‑профит абсолютной ценой.
- `--poll` (float, сек): частота проверки брекетов (для dry‑run сопровождения).
- `--log-file` (str): путь к файлу логов.
- `--trade-log` (str): путь к CSV‑логу сделок.
- `--dry-run` (bool): сухой режим HL (по умолчанию `True`).
- `--hl-api-secret` (str): приватный ключ (hex) для реальных ордеров.
- `--use-testnet` (bool): использовать тестнет (по умолчанию False → мейннет).
- `--verbose` (bool): подробный вывод.

Примеры:
```bash
# Dry-run, сайз в USD, изолированная маржа
python3 -m bot.main short --alt-symbol ETHUSDT \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.5 --tp 2.0 --poll 2 --dry-run \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv

# Тестнет, реальные ордера
python3 -m bot.main short --alt-symbol ETHUSDT \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.5 --tp 2.0 --use-testnet \
  --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX \
  --dry-run False
```

### 4) Симуляция падения BTC → реальный вход (`simulate_btc_fall`)
- Каждые `interval` секунд BTC снижается на `fall_step_pct` процентов от текущего
- Когда падение от стартового уровня достигает `threshold` процентов — открывается реальный шорт по `alt-symbol` с SL/TP
- Источник цен — HL Info (тестнет/мейннет)

Флаги:
- `--alt-symbol` (str): альта для входа.
- `--threshold` (float): порог падения BTC (%) для входа.
- `--qty` (float): размер позиции (монеты) если не используется `--usd-notional`.
- `--usd-notional` (float): размер позиции в USD.
- `--sl`/`--tp` (float, %): стоп‑лосс/тейк‑профит от цены входа.
- `--leverage` (int), `--isolated` (bool): режим маржи.
- `--interval` (сек): интервал симуляции (по умолчанию 2).
- `--fall-step-pct` (%): шаг падения BTC за интервал (по умолчанию 0.1).
- `--log-file`, `--trade-log`.
- `--hl-api-secret` (hex): ключ для реальных ордеров.
- `--use-testnet` (bool): тестнет (True) или мейннет (False).
- `--verbose` (bool).

Примеры:
```bash
# Тестнет (безопасно)
python3 -m bot.main simulate_btc_fall \
  --alt-symbol ETHUSDT \
  --threshold 2.0 \
  --usd-notional 50 \
  --sl 2.0 --tp 2.0 \
  --leverage 3 --isolated \
  --interval 2 --fall-step-pct 0.1 \
  --use-testnet \
  --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX

# Мейннет (реальные средства!)
python3 -m bot.main simulate_btc_fall \
  --alt-symbol ETHUSDT \
  --threshold 2.0 \
  --usd-notional 50 \
  --sl 2.0 --tp 2.0 \
  --leverage 3 --isolated \
  --interval 2 --fall-step-pct 0.1 \
  --use-testnet False \
  --hl-api-secret 0xYOUR_MAINNET_PRIVATE_KEY_HEX
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

# Мгновенный шорт без стратегии (dry-run)
python3 -m bot.main short --alt-symbol ETHUSDT --qty 1 --leverage 3 --sl 1.5 --tp 2.0 --dry-run
```