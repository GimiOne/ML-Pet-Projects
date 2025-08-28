# Бот: шорт альткоина при падении BTC

Идея: при резком падении BTC у нас есть короткое «окно» (обычно до ~30 минут, а сильнейшее движение в первые ~10 минут), чтобы зайти в шорт по выбранной альте из топ-30. Этот бот автоматизирует детект падения BTC и выставляет шорт по альте на Hyperliquid c использованием официального SDK.

Возможности:
- Стратегия: детект падения BTC → шорт альты, SL/TP
- Мгновенная команда `short`: рыночный шорт без стратегии (USD-сайзинг, изолированная маржа, SL/TP)
- Симуляция падения BTC и (опционально) симуляция альты с реальным входом и управлением позицией
- Логи в консоль и в файл + CSV-лог сделок (PnL)

## Структура
```
/workspace/bot
  ├─ prices/                # Поставщики цен (Binance, HL Info, Manual)
  ├─ exchanges/hl.py        # Hyperliquid SDK клиент (order/trigger, cross/isolated, округления)
  ├─ strategy/              # Логика стратегии
  ├─ scripts/hl_short_test.py # Автономный тест шорта на HL (SDK)
  ├─ main.py                # CLI (Typer): run-live / manual-*/ short / simulate-btc-fall
  ├─ logging_utils.py, config.py, requirements.txt, README.md
```

## Установка
```bash
python3 -m pip install --break-system-packages -r /workspace/bot/requirements.txt
```

## Ключевые команды
- run-live: онлайн-цены Binance, dry-run стратегия
- manual-once / manual-replay: ручные цены (dry-run), отладка стратегии
- short: мгновенный шорт (SDK), USD-сайзинг, изолированная маржа, SL/TP, тестнет/мейннет
- simulate-btc-fall: симуляция BTC (и опционально ALT) → реальный вход на HL, SL/TP, расширенные логи

## Примеры
### Мгновенный шорт (SDK)
- Dry-run, сайз в USD, изолированная маржа:
```bash
python3 -m bot.main short --alt-symbol ETHUSDT \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.5 --tp 2.0 --poll 2 --dry-run \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv
```
- Тестнет (реальные ордера на тестовой сети):
```bash
python3 -m bot.main short --alt-symbol ETHUSDT \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.5 --tp 2.0 --use-testnet \
  --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX \
  --dry-run False
```

### Симуляция падения BTC → реальный вход (SDK)
- Тестнет (безопасно), симуляция ALT следует за BTC, закрытие по срабатыванию на симуляции:
```bash
python3 -m bot.main simulate-btc-fall \
  --alt-symbol ETHUSDT \
  --threshold 2.0 \
  --usd-notional 50 \
  --sl 1.0 --tp 1.0 \
  --leverage 3 --isolated \
  --interval 2 --fall-step-pct 0.1 \
  --sim-alt --alt-mode follow --alt-beta 1.2 \
  --close-on-sim-hit \
  --use-testnet \
  --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX
```
- Мейннет (реальные средства!) с параметрами по вашему запросу:
```bash
python3 -m bot.main simulate-btc-fall \
  --alt-symbol ETHUSDT \
  --threshold 2.0 \
  --usd-notional 50 \
  --sl 1.0 --tp 1.0 \
  --leverage 3 --isolated \
  --interval 2 --fall-step-pct 0.1 \
  --sim-alt --alt-mode follow --alt-beta 1.2 \
  --close-on-sim-hit \
  --use-testnet False \
  --hl-api-secret 0xYOUR_MAINNET_PRIVATE_KEY_HEX
```

## Подробный CLI (--help)
Ниже — сводка флагов, соответствующая текущему коду.

### short — мгновенный шорт с HL SDK
- --alt-symbol (str): символ альты, напр. ETHUSDT
- --qty (float): размер позиции (монеты), если не задан --usd-notional
- --usd-notional (float): размер в USD, перекрывает --qty
- --leverage (int): плечо для режима маржи
- --isolated (bool): изолированная маржа (по умолчанию cross)
- --sl / --tp (float, %): стоп‑лосс и тейк‑профит от цены входа
- --sl-price / --tp-price (float): альтернативно задать уровни абсолютной ценой
- --poll (сек): интервал опроса (только для dry‑run сопровождения)
- --log-file (str): файл логов, по умолчанию /workspace/bot/logs/bot.log
- --trade-log (str): CSV лог сделок, по умолчанию /workspace/bot/logs/trades.csv
- --dry-run (bool): по умолчанию True (без реальных ордеров)
- --hl-api-secret (hex): приватный ключ кошелька для реальных ордеров
- --use-testnet (bool): тестнет (True) или мейннет (False)
- --verbose (bool)

### simulate-btc-fall — симуляция BTC/ALT → реальный вход
- --alt-symbol (str): альта для входа
- --threshold (float, %): порог падения BTC от стартового уровня для входа
- --qty (float) | --usd-notional (float): размер позиции (монеты или USD)
- --sl / --tp (float, %): цели выхода от цены входа (ставятся и как on-chain триггеры)
- --leverage (int), --isolated (bool): установка режима маржи на HL
- --interval (сек): период симуляции (по умолчанию 2)
- --fall-step-pct (%, float): шаг изменения BTC за интервал (по умолчанию 0.1)
- --sim-alt (bool): включить симуляцию цены альты
- --alt-mode (str): follow|drop|rise (поведение альты)
- --alt-beta (float): чувствительность альты к шагам BTC при режиме follow
- --close-on-sim-hit (bool): закрывать реальную позицию маркетом, если сим‑цена достигла SL/TP
- --log-file, --trade-log
- --hl-api-secret (hex)
- --use-testnet (bool)
- --verbose (bool)

### run-live — стратегия в реальном времени (Binance цены, вход на HL)
- Описание: опрашивает Binance цены, вычисляет BTC drawdown за окно `--lookback`. Когда падение ≥ `--threshold`, входит в шорт по `--alt`, сайзит позицию по `--usd-notional` или `--qty`, устанавливает маржу cross/isolated, плечо, и размещает SL/TP триггеры на HL.
- Флаги:
  - `--alt` (str): символ альты, напр. ETHUSDT
  - `--threshold` (float, %): порог падения BTC от локального максимума
  - `--lookback` (сек): окно поиска локального максимума BTC
  - `--usd-notional` (float): размер позиции в USD (перекрывает `--qty`)
  - `--qty` (float): размер позиции (монеты), если не указан `--usd-notional`
  - `--leverage` (float): плечо, устанавливается в режиме маржи
  - `--isolated` (bool): изолированная маржа (по умолчанию cross)
  - `--sl`/`--tp` (float, %): стоп‑лосс/тейк‑профит от цены входа (ставятся как триггер‑ордера)
  - `--poll` (сек): период опроса
  - `--log-file` (str): файл логов, по умолчанию `/workspace/bot/logs/bot.log`
  - `--trade-log` (str): CSV лог сделок, по умолчанию `/workspace/bot/logs/trades.csv`
  - `--use-testnet` (bool): тестнет (True) или мейннет (False)
  - `--hl-api-secret` (hex): приватный ключ кошелька для реальных ордеров
  - `--dry-run` (bool): сухой режим
  - `--verbose` (bool)

- Пример (тестнет):
```bash
python3 -m bot.main run-live \
  --alt ETHUSDT \
  --threshold 2.0 --lookback 300 \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.0 --tp 1.0 \
  --poll 2 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --use-testnet \
  --hl-api-secret 0xYOUR_TESTNET_PRIVATE_KEY_HEX \
  --dry-run False
```
- Пример (мейннет, реальные средства!):
```bash
python3 -m bot.main run-live \
  --alt ETHUSDT \
  --threshold 2.0 --lookback 300 \
  --usd-notional 50 --leverage 3 --isolated \
  --sl 1.0 --tp 1.0 \
  --poll 2 \
  --log-file /workspace/bot/logs/bot.log \
  --trade-log /workspace/bot/logs/trades.csv \
  --use-testnet False \
  --hl-api-secret 0xYOUR_MAINNET_PRIVATE_KEY_HEX \
  --dry-run False
```

### Как интерпретировать BTC drawdown
- Рассчитывается как падение текущей цены от локального максимума в окне `--lookback`:
  drawdown% = (local_max - current_price) / local_max * 100.
- Обновляется на каждом тике, но если в окне ещё не появился новый максимум выше текущего, показатель может долго оставаться близким к прежнему значению или 0.0%, даже если BTC «шевелится» в узком диапазоне. Значение быстро меняется при новых экстремумах (обновлении max), либо при значимых движениях вниз от недавно сформированного максимума.

### manual-once / manual-replay — ручные цены
- manual-once: --btc, --alt, --alt-symbol, --threshold, --lookback, --qty, --leverage, --sl, --tp, --log-file, --trade-log, --dry-run, --verbose
- manual-replay: --btc-seq, --alt-seq, --alt-symbol, --threshold, --lookback, --qty, --leverage, --sl, --tp, --log-file, --trade-log, --dry-run, --verbose, --step-delay

## Логи и PnL
- Консоль/файл: текущие цены BTC, ALT(реальная) и ALT(симулированная, если включено), падение BTC, PnL real/sim, постановка SL/TP, установка маржи/плеча.
- CSV (trades.csv): фиксирует вход/выход, цены, размер, PnL и причину (tp/sl/manual).

## Важно
- Мейннет: реальные средства. Используйте осторожно, протестируйте на тестнете.
- Размеры и цены приводятся к шагам инструмента (szDecimals, правила SDK).
- При проблемах с валидностью цены/размера — уменьшите USD‑ноционал/шаги или пришлите символ и уровни.