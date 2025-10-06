ниже — готовая инструкция для Cursor, чтобы превратить твою панель в режим «Покупай / Держи / Продавай» + дать простые подсказки и объём покупки. Я написал её как серию коротких задач с текстами-промптами, которые можно подряд кидать в Cursor. Кодовые блоки — минимальные скелеты, Cursor допишет детали.

---

# 0) Предпосылки (что уже есть)

* Python backend (FastAPI) + ежедневный сбор данных (moexalgo/ISS) → `data/analysis.json`.
* В JSON на тикер есть: `price`, `sma20/50/200`, `dy_ttm`, `trend_pct`, `high_52w`, `low_52w`, сигналы и т.п.
* UI (твоя панель) показывает списки с DY, SMA200, трендом и сигналами.

---

# 1) Добавляем «движок правил» (rules engine)

## Задача для Cursor

**Промпт:**
«Создай модуль `app/reco/engine.py`. В нём реализуй функцию `make_reco(t: TickerSnapshot, cfg: RecoConfig) -> Recommendation`, где:

* `TickerSnapshot` — dataclass со всеми нужными полями из analysis.json,
* `RecoConfig` — границы и веса правил (порог DY, отклонения от SMA и т.д.),
* `Recommendation` — dataclass: `action: Literal["BUY","HOLD","SELL"]`, `score: float`, `reasons: list[str]`, `sizing_hint: str | None`.
  Сделай скoring-подход: каждое правило добавляет/снимает баллы. Итог: BUY если score ≥ +2, SELL если ≤ −2, иначе HOLD.»

**Скелет кода:**

```python
# app/reco/models.py
from dataclasses import dataclass
from typing import Literal, List, Optional

Action = Literal["BUY", "HOLD", "SELL"]

@dataclass
class TickerSnapshot:
    symbol: str
    price: float
    sma20: float | None
    sma50: float | None
    sma200: float | None
    dy_ttm: float | None
    trend_pct_20d: float | None
    high_52w: float | None
    low_52w: float | None
    sector: str | None = None
    vol_avg_20d: float | None = None

@dataclass
class Recommendation:
    action: Action
    score: float
    reasons: List[str]
    sizing_hint: Optional[str] = None

@dataclass
class RecoConfig:
    dy_buy_min: float          # например 8.0 (%)
    dy_very_high: float        # напр. 15.0
    max_discount_vs_sma200: float # напр. -10.0 (%)
    min_premium_vs_sma200: float  # напр. +10.0 (%)
    trend_up_min: float        # напр. +0.5 (% за 20д)
    trend_down_max: float      # напр. -0.5
    buy_score_cutoff: float    # 2.0
    sell_score_cutoff: float   # -2.0
```

```python
# app/reco/engine.py
from .models import TickerSnapshot, RecoConfig, Recommendation

def pct(a: float, b: float) -> float:
    if a is None or b in (None, 0): return 0.0
    return (a - b) / b * 100.0

def make_reco(t: TickerSnapshot, cfg: RecoConfig) -> Recommendation:
    score = 0.0
    reasons = []

    # 1) Дивиденды
    if t.dy_ttm is not None and t.dy_ttm >= cfg.dy_buy_min:
        score += 1.5
        reasons.append(f"DY {t.dy_ttm:.2f}% ≥ {cfg.dy_buy_min}%")
        if t.dy_ttm >= cfg.dy_very_high:
            score += 0.5
            reasons.append(f"очень высокая DY {t.dy_ttm:.2f}%")

    # 2) Позиция к SMA200 (дисконт/премия)
    if t.sma200:
        d_vs_sma200 = pct(t.price, t.sma200)
        if d_vs_sma200 <= cfg.max_discount_vs_sma200:
            score += 1.0
            reasons.append(f"цена {d_vs_sma200:.1f}% ниже SMA200")
        if d_vs_sma200 >= cfg.min_premium_vs_sma200:
            score -= 1.0
            reasons.append(f"цена {d_vs_sma200:.1f}% выше SMA200")

    # 3) Краткосрочный тренд
    if t.trend_pct_20d is not None:
        if t.trend_pct_20d >= cfg.trend_up_min:
            score += 0.8
            reasons.append(f"положительный тренд {t.trend_pct_20d:.1f}%")
        if t.trend_pct_20d <= cfg.trend_down_max:
            score -= 0.8
            reasons.append(f"отрицательный тренд {t.trend_pct_20d:.1f}%")

    # 4) Расстояние до 52W экстремумов (контртрендовый вход)
    if t.high_52w and t.low_52w and t.price:
        in_range = (t.price - t.low_52w) / max(1e-9, (t.high_52w - t.low_52w))
        # ближе к 0 → низ диапазона, ближе к 1 → верх
        if in_range < 0.3:
            score += 0.5
            reasons.append("цена в нижней трети 52W диапазона")
        elif in_range > 0.9:
            score -= 0.5
            reasons.append("цена у верхней границы 52W диапазона")

    # Финальное действие
    if score >= cfg.buy_score_cutoff:
        action = "BUY"
    elif score <= cfg.sell_score_cutoff:
        action = "SELL"
    else:
        action = "HOLD"

    sizing = sizing_hint(action, t)
    return Recommendation(action=action, score=round(score, 2), reasons=reasons, sizing_hint=sizing)

def sizing_hint(action: str, t: TickerSnapshot) -> str | None:
    if action == "BUY":
        # очень простая эвристика: чем ниже к SMA200 и выше DY — тем больше ставка
        if (t.sma200 and t.price and (t.price < 0.9 * t.sma200)) and (t.dy_ttm and t.dy_ttm >= 12):
            return "Совет: увеличить позицию до 1.5× от базовой доли"
        return "Совет: базовая доля (1×)"
    if action == "SELL":
        return "Совет: сократить позицию на 25–50%"
    return None
```

---

# 2) Конфиг порогов в YAML

## Задача для Cursor

**Промпт:**
«Добавь файл `config/reco.yaml` с дефолтными порогами. Реализуй загрузку в `app/reco/config.py`.»

**Пример YAML:**

```yaml
dy_buy_min: 8.0
dy_very_high: 15.0
max_discount_vs_sma200: -10.0
min_premium_vs_sma200: 10.0
trend_up_min: 0.5
trend_down_max: -0.5
buy_score_cutoff: 2.0
sell_score_cutoff: -2.0
```

Лоадер:

```python
# app/reco/config.py
import yaml
from .models import RecoConfig

def load_reco_cfg(path="config/reco.yaml") -> RecoConfig:
    with open(path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return RecoConfig(**d)
```

---

# 3) Чтение `analysis.json` и выдача рекомендаций

## Задача для Cursor

**Промпт:**
«Сделай модуль `app/reco/service.py`, который:

1. читает `data/analysis.json`;
2. маппит записи в `TickerSnapshot`;
3. прогоняет через `make_reco`;
4. возвращает список рекомендаций;
   Добавь FastAPI эндпоинт `/recommendations` с параметрами `only=["BUY","SELL","HOLD"]` и `min_score`.»

**Скелет:**

```python
# app/reco/service.py
import json
from pathlib import Path
from typing import List
from .models import TickerSnapshot, Recommendation
from .engine import make_reco
from .config import load_reco_cfg

def load_analysis(path="data/analysis.json") -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_snapshots(rows: list[dict]) -> List[TickerSnapshot]:
    snaps = []
    for r in rows:
        snaps.append(TickerSnapshot(
            symbol=r["symbol"],
            price=r.get("price"),
            sma20=r.get("sma20"), sma50=r.get("sma50"), sma200=r.get("sma200"),
            dy_ttm=r.get("dy_ttm"),
            trend_pct_20d=r.get("trend_pct_20d"),
            high_52w=r.get("high_52w"),
            low_52w=r.get("low_52w"),
            sector=r.get("sector"),
            vol_avg_20d=r.get("vol_avg_20d"),
        ))
    return snaps

def get_recommendations(only=None, min_score=None) -> List[dict]:
    cfg = load_reco_cfg()
    rows = load_analysis()
    snaps = build_snapshots(rows)
    out = []
    for s in snaps:
        rec = make_reco(s, cfg)
        if only and rec.action not in only: 
            continue
        if min_score is not None and rec.score < min_score:
            continue
        out.append({
            "symbol": s.symbol,
            "price": s.price,
            "action": rec.action,
            "score": rec.score,
            "reasons": rec.reasons,
            "sizing_hint": rec.sizing_hint
        })
    return out
```

```python
# app/api/routes_reco.py
from fastapi import APIRouter, Query
from typing import List, Optional
from app.reco.service import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("")
def recommendations(
    only: Optional[List[str]] = Query(default=None),
    min_score: Optional[float] = None
):
    return {"items": get_recommendations(only, min_score)}
```

И зарегистрируй роутер в основном `app/main.py`.

---

# 4) UI: две кнопки и объяснение «почему»

## Задача для Cursor

**Промпт:**
«В фронтенде добавь вкладку `Решения` с тремя списками: BUY / HOLD / SELL. Для каждого тикера показывай:

* крупную кнопку («Покупай» зелёная, «Продавай» красная, «Держи» серая),
* score (бейдж),
* краткие причины (tooltip),
* sizing_hint («базовая доля», «увеличить до 1.5×»).
  Данные брать из `/recommendations?only=...`.
  Сортировка: BUY по убыванию score, SELL по возрастанию score.»

Если у тебя фронт на React:

* создай компонент `RecommendationsPage.tsx`,
* используй простой `fetch` к FastAPI,
* добавь фильтры сверху (радиокнопки BUY/HOLD/SELL),
* цветовые бейджи.

---

# 5) Учёт портфеля: «что делать именно мне»

Чтобы кнопки учитывали твои текущие позиции/кэш, добавим эндпоинт, который соединяет рекомендации + твой `portfolio.json`.

## Задача для Cursor

**Промпт:**
«Создай эндпоинт `POST /my/actions`:

* читает `data/portfolio.json`,
* берёт `/recommendations`,
* для каждого BUY рассчитывает возможную покупку на базовую долю (например 5% от портфеля) или на доступный кэш, формирует `qty_suggested`,
* для SELL — предлагает сократить 25/50% текущей позиции, если она есть.
  Верни массив с полями: `symbol, action, qty_suggested, cash_impact, reasons, sizing_hint`.»

Скелет расчёта:

```python
# app/reco/personalize.py
import json
from pathlib import Path

def load_portfolio(path="data/portfolio.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def portfolio_value(p):
    return p.get("cash", 0) + sum(pos["current_value"] for pos in p["positions"])

def suggest_actions(recos, p):
    total = portfolio_value(p)
    cash = p.get("cash", 0)
    base_target = 0.05 * total  # базовая доля 5%
    held = {pos["symbol"]: pos for pos in p["positions"]}
    out = []
    for r in recos:
        if r["action"] == "BUY":
            budget = min(base_target, cash)
            qty = int(budget // (r["price"] or 1))
            out.append({**r, "qty_suggested": qty, "cash_impact": -(qty * r["price"])})
        elif r["action"] == "SELL" and r["symbol"] in held:
            have_qty = int(held[r["symbol"]]["qty"])
            qty = max(1, have_qty // 4)  # сократить на ~25%
            out.append({**r, "qty_suggested": qty, "cash_impact": +(qty * r["price"])})
    return out
```

Эндпоинт:

```python
# app/api/routes_my.py
from fastapi import APIRouter
from app.reco.service import get_recommendations
from app.reco.personalize import load_portfolio, suggest_actions

router = APIRouter(prefix="/my", tags=["my"])

@router.get("/actions")
def my_actions():
    p = load_portfolio()
    recos = get_recommendations()
    return {"items": suggest_actions(recos, p)}
```

UI-кнопки «Купить N» / «Продать N» могут просто копировать количество в буфер/открывать модалку с подсказкой (мы не ходим к брокеру).

---

# 6) Настройки «в одну кнопку»

Добавь страницу **Настройки → Правила**:

* Порог DY,
* Порог отклонения от SMA200,
* Порог тренда,
* Границы BUY/SELL по score.
  Эти параметры редактируют `config/reco.yaml` (эндпоинт `PUT /config/reco`).

---

# 7) Мини-бэктест (по желанию)

Чтобы проверить, что правила адекватны: возьми дневные свечи за N месяцев и симулируй:

* BUY при появлении BUY-рекомендации, SELL при SELL, иначе HOLD.
  Сделай простую страницу «Бэктест» с кривой эквити.

---

# 8) Приёмка (что должно работать)

* `/recommendations` возвращает для всех тикеров действие, score, причины, sizing_hint.
* В UI вкладка «Решения» даёт три списка с цветными кнопками.
* `/my/actions` учитывает `portfolio.json` и кэш, предлагает количество.
* Изменение `config/reco.yaml` меняет рекомендации без перекомпиляции.
* Всё не падает, если каких-то полей (sma/dy/trend) нет — правила пропускают такие пункты.

---

# 9) Стартовые значения (подойдёт под твой скрин)

* `dy_buy_min: 8`
* `dy_very_high: 15`
* `max_discount_vs_sma200: -10`
* `min_premium_vs_sma200: 10`
* `trend_up_min: 0.5`
* `trend_down_max: -0.5`
* `buy_score_cutoff: 2`
* `sell_score_cutoff: -2`

---

Если хочешь — дополню «черный список» (исключить бумаги, где DY аномально высок из-за разовых выплат) и «белый список» (стратегические бумаги, всегда HOLD/докупать только на просадках).
