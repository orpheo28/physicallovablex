"""Fictional production network — store + the 7 PRD §10 tools as plain Python. Owner: W5.

No MCP import here: `factory_mcp.server` exposes these functions over MCP, and
`api/agents/negotiation` uses them in-process (stage 7/8 handlers + the factory-portal provider).

Everything in this network is **Fictional — demo data** (record-level `label: "fictional"`).
Capacity data does not exist publicly (E_usines.md): the network *creates* it through
`register_capacity`; the seed partners (factories, integrator, installers) stand in for onboarded factories.

Storage: SQLite (stdlib), one JSON document per record, path resolved at every call:
  1. $FACTORY_MCP_DB
  2. next to $DB_PATH (the API's database) as `factory_network.db` — keeps tests/deployments isolated
  3. factory_mcp/data/network.db (runtime state, gitignored)
Seed factories (data/factories.json) and seed RFQs (data/seed_rfqs.json) are inserted on first use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from contracts.artifacts import (
    process_label,
    RFQ,
    CapacityProfile,
    Factory,
    FactoryMatch,
    LabeledValue,
    Model,
    PastPerformance,
    ProcessType,
    Quote,
    QuoteStatus,
    QuoteTier,
    RFQStatus,
    RFQWithQuotes,
    ScoreComponent,
    SearchCapacityQuery,
    utcnow,
)
from pydantic import Field

DATA_DIR = Path(__file__).resolve().parent / "data"
SEED_FACTORIES = DATA_DIR / "factories.json"
SEED_RFQS = DATA_DIR / "seed_rfqs.json"

# search_capacity weights (sum = 1). Exposed so the UI/README can show them.
WEIGHTS: dict[str, float] = {
    "process_fit": 0.35,
    "moq": 0.15,
    "certifications": 0.15,
    "load": 0.15,
    "lead_time": 0.20,
}

ANY_MATERIAL = {"", "any", "mixed", "n/a"}
FICTIONAL_SCORE_NOTE = "Scored on demo data (fictional network)"


class NotFoundError(KeyError):
    """Unknown factory / RFQ / quote id."""


class OrderDraft(Model):
    """Output of `accept_quote` (PRD §10: 'order draft')."""

    order_id: str
    quote_id: str
    rfq_id: str
    factory_id: str
    factory_name: str
    tiers: list[QuoteTier]
    tooling_usd: float
    moq: int
    lead_time_days: int
    payment_terms: str
    status: str = "draft"
    label: str = Field(default="fictional")


# --------------------------------------------------------------------------- store


def db_path() -> Path:
    if p := os.getenv("FACTORY_MCP_DB"):
        return Path(p)
    if p := os.getenv("DB_PATH"):  # one network store per API database: isolated dev/test DBs never share it
        app_db = Path(p)
        return app_db.with_name("factory_network.db" if app_db.stem == "app" else f"{app_db.stem}_network.db")
    return DATA_DIR / "network.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS factory (id TEXT PRIMARY KEY, data TEXT NOT NULL, seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rfq (id TEXT PRIMARY KEY, factory_id TEXT NOT NULL, product_name TEXT NOT NULL,
                                data TEXT NOT NULL, seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS quote (id TEXT PRIMARY KEY, rfq_id TEXT NOT NULL, version INTEGER NOT NULL,
                                  data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_draft (id TEXT PRIMARY KEY, quote_id TEXT NOT NULL, data TEXT NOT NULL);
"""


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    try:
        con.execute("PRAGMA journal_mode=WAL")  # readers (factory portal) never wait on a negotiation write
        con.execute("PRAGMA busy_timeout=10000")
        con.executescript(_SCHEMA)
        if con.execute("SELECT COUNT(*) FROM factory").fetchone()[0] == 0:
            _seed(con)
        elif str(path) not in _SEEDED:  # W20: seed records added later (the 3 installers) reach stores created before them
            _seed_missing_factories(con)
        _SEEDED.add(str(path))
        yield con
        con.commit()
    finally:
        con.close()


def _seed(con: sqlite3.Connection) -> None:
    for i, raw in enumerate(json.loads(SEED_FACTORIES.read_text())):
        f = Factory.model_validate(raw)
        con.execute("INSERT OR IGNORE INTO factory VALUES (?, ?, ?)", (f.id, f.model_dump_json(), i))
    if SEED_RFQS.exists():
        for i, raw in enumerate(json.loads(SEED_RFQS.read_text())):
            item = RFQWithQuotes.model_validate(raw)
            con.execute(
                "INSERT OR IGNORE INTO rfq VALUES (?, ?, ?, ?, ?)",
                (item.rfq.id, item.rfq.factory_id, item.product_name, item.rfq.model_dump_json(), i),
            )
            for q in item.quotes:
                con.execute("INSERT OR IGNORE INTO quote VALUES (?, ?, ?, ?)", (q.id, q.rfq_id, q.version, q.model_dump_json()))


_SEEDED: set[str] = set()


def _seed_missing_factories(con: sqlite3.Connection) -> None:
    seq = con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM factory").fetchone()[0]
    for i, raw in enumerate(json.loads(SEED_FACTORIES.read_text())):
        f = Factory.model_validate(raw)
        con.execute("INSERT OR IGNORE INTO factory VALUES (?, ?, ?)", (f.id, f.model_dump_json(), seq + i))


def reset() -> None:
    """Drop all runtime state (registered factories, RFQs, quotes, orders) and re-seed."""
    path = db_path()
    if path.exists():
        path.unlink()
    with _conn():
        pass


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# --------------------------------------------------------------------------- reads


def partner_kind(factory_id: str, archetype: str) -> str:
    """W21b: factory | installer | integrator (records stored before the field existed get it inferred)."""
    a = (archetype or "").lower()
    if factory_id.startswith("i_") or "installer" in a:
        return "installer"
    return "integrator" if "integrator" in a else "factory"


def _load(raw: str) -> Factory:
    f = Factory.model_validate_json(raw)
    if '"kind"' not in raw:
        f.kind = partner_kind(f.id, f.archetype)
    return f


def list_factories() -> list[Factory]:
    with _conn() as con:
        rows = con.execute("SELECT data FROM factory ORDER BY seq, id").fetchall()
    return [_load(r[0]) for r in rows]


def get_factory(factory_id: str) -> Factory | None:
    with _conn() as con:
        row = con.execute("SELECT data FROM factory WHERE id = ?", (factory_id,)).fetchone()
    return _load(row[0]) if row else None


def _require_factory(factory_id: str) -> Factory:
    f = get_factory(factory_id)
    if f is None:
        raise NotFoundError(f"factory {factory_id} not found")
    return f


def get_rfq(rfq_id: str) -> RFQ:
    with _conn() as con:
        row = con.execute("SELECT data FROM rfq WHERE id = ?", (rfq_id,)).fetchone()
    if not row:
        raise NotFoundError(f"rfq {rfq_id} not found")
    return RFQ.model_validate_json(row[0])


def get_quote(quote_id: str) -> Quote:
    with _conn() as con:
        row = con.execute("SELECT data FROM quote WHERE id = ?", (quote_id,)).fetchone()
    if not row:
        raise NotFoundError(f"quote {quote_id} not found")
    return Quote.model_validate_json(row[0])


def list_quotes(rfq_id: str) -> list[Quote]:
    with _conn() as con:
        rows = con.execute("SELECT data FROM quote WHERE rfq_id = ? ORDER BY version", (rfq_id,)).fetchall()
    return [Quote.model_validate_json(r[0]) for r in rows]


def list_rfqs(factory_id: str) -> list[RFQWithQuotes]:
    """Factory-portal view: RFQs received by a factory, newest first, with every quote version."""
    with _conn() as con:
        rows = con.execute(
            "SELECT data, product_name FROM rfq WHERE factory_id = ? ORDER BY seq DESC", (factory_id,)
        ).fetchall()
    out = []
    for data, product_name in rows:
        rfq = RFQ.model_validate_json(data)
        out.append(RFQWithQuotes(rfq=rfq, product_name=product_name, quotes=list_quotes(rfq.id)))
    return out


def _save_rfq(con: sqlite3.Connection, rfq: RFQ, product_name: str | None = None) -> None:
    if product_name is None:
        con.execute("UPDATE rfq SET data = ? WHERE id = ?", (rfq.model_dump_json(), rfq.id))
        return
    seq = con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM rfq").fetchone()[0]
    con.execute("INSERT INTO rfq VALUES (?, ?, ?, ?, ?)", (rfq.id, rfq.factory_id, product_name, rfq.model_dump_json(), seq))


def _save_quote(con: sqlite3.Connection, q: Quote) -> None:
    con.execute("INSERT OR REPLACE INTO quote VALUES (?, ?, ?, ?)", (q.id, q.rfq_id, q.version, q.model_dump_json()))


# --------------------------------------------------------------------------- tool 1: register_capacity


def register_capacity(
    name: str,
    region: str,
    processes: list[str],
    materials: list[str],
    moq: int,
    certifications: list[str],
    lead_time_days: int,
    monthly_capacity: int,
    current_load_pct: float,
    archetype: str = "balanced",
    personality: str | None = None,
) -> str:
    """Factory onboarding: creates the capacity record the market lacks. Returns factory_id."""
    if not name.endswith("(fictional)"):
        name = f"{name} (fictional)"
    fid = _new_id("f")
    factory = Factory(
        id=fid,
        kind=partner_kind(fid, archetype),
        name=name,
        region=region,
        archetype=archetype,
        personality=personality,
        capacity=CapacityProfile(
            processes=[ProcessType(p) for p in processes],
            materials=materials,
            moq=moq,
            certifications=certifications,
            lead_time_days=lead_time_days,
            monthly_capacity=monthly_capacity,
            current_load_pct=current_load_pct,
        ),
        audit_notes=["Self-registered via register_capacity — not audited"],
        past_performance=PastPerformance(orders_completed=0, on_time_rate_pct=None, defect_rate_pct=None, no_data=True),
    )
    with _conn() as con:
        seq = con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM factory").fetchone()[0]
        con.execute("INSERT INTO factory VALUES (?, ?, ?)", (factory.id, factory.model_dump_json(), seq))
    return factory.id


# --------------------------------------------------------------------------- tool 2: search_capacity


def _tokens(s: str) -> set[str]:
    return {t for t in s.lower().replace("+", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if t}


def material_match(query_material: str, factory_materials: list[str]) -> str | None:
    """First factory material whose leading token is a token of the query (or equal to it)."""
    q = query_material.strip().lower()
    qt = _tokens(q)
    for m in factory_materials:
        ml = m.lower()
        lead = ml.split()[0] if ml.split() else ml
        if ml == q or ml in qt or lead in qt:
            return m
    return None


def _clamp(x: float) -> float:
    return round(max(0.0, min(1.0, x)), 2)


def score_factory(factory: Factory, query: SearchCapacityQuery, today: date | None = None) -> list[ScoreComponent]:
    """Deterministic 5-criterion breakdown (process_fit, moq, certifications, load, lead_time)."""
    cap = factory.capacity
    # process fit
    has_process = query.process in cap.processes
    any_material = query.material.strip().lower() in ANY_MATERIAL
    mat = "any material" if any_material else material_match(query.material, cap.materials)
    if has_process and mat:
        pf, pf_note = 1.0, f"Runs {process_label(query.process)} in {mat}"
    elif has_process:
        pf, pf_note = 0.6, f"Runs {process_label(query.process)}, but {query.material} is not in its material list"
    else:
        pf, pf_note = 0.0, f"Does not run {process_label(query.process)}"
    # W21: a category specialist (lighting, wearables, drones…) is a weaker fit for another category
    cats = [c.lower() for c in getattr(cap, "categories", None) or []]
    if pf > 0 and query.category and cats:
        if query.category.lower() in cats:
            pf_note += f" — {query.category.replace('_', ' ')} specialist"
        else:
            pf = round(pf * 0.5, 2)
            pf_note += f" — specialises in {', '.join(c.replace('_', ' ') for c in cats)}, not {query.category.replace('_', ' ')}"
    # moq
    if cap.moq <= query.quantity:
        mq, mq_note = 1.0, f"MOQ {cap.moq:,} ≤ {query.quantity:,} units"
    else:
        mq, mq_note = _clamp(query.quantity / cap.moq), f"MOQ {cap.moq:,} > {query.quantity:,} units"
    # certifications
    req = query.certifications_required
    held = [c for c in req if c.lower() in {x.lower() for x in cap.certifications}]
    if not req:
        ce, ce_note = 1.0, "No factory certification required" + (f" (holds {', '.join(cap.certifications)})" if cap.certifications else "")
    else:
        ce = _clamp(len(held) / len(req))
        missing = [c for c in req if c not in held]
        ce_note = f"Holds {', '.join(held) or 'none'} of {', '.join(req)}" + (f"; missing {', '.join(missing)}" if missing else "")
    # load
    ld = _clamp((95 - cap.current_load_pct) / 50)
    free = int(cap.monthly_capacity * max(0.0, 100 - cap.current_load_pct) / 100)
    ld_note = f"{cap.current_load_pct:.0f}% loaded, ~{free:,} units/month free"
    # lead time
    lt = _clamp((60 - cap.lead_time_days) / 40)
    lt_note = f"{cap.lead_time_days}-day lead time"
    if query.deadline is not None:
        days_left = (query.deadline - (today or date.today())).days
        if cap.lead_time_days > days_left:
            lt = _clamp(lt * 0.5)
            lt_note += f" — misses the deadline ({days_left} days left)"
        else:
            lt_note += f" — fits the deadline ({days_left} days left)"
    return [
        ScoreComponent(criterion="process_fit", score=pf, weight=WEIGHTS["process_fit"], note=pf_note),
        ScoreComponent(criterion="moq", score=mq, weight=WEIGHTS["moq"], note=mq_note),
        ScoreComponent(criterion="certifications", score=ce, weight=WEIGHTS["certifications"], note=ce_note),
        ScoreComponent(criterion="load", score=ld, weight=WEIGHTS["load"], note=ld_note),
        ScoreComponent(criterion="lead_time", score=lt, weight=WEIGHTS["lead_time"], note=lt_note),
    ]


def total_score(breakdown: list[ScoreComponent]) -> float:
    return round(100 * sum(c.score * c.weight for c in breakdown), 1)


def _reasons(factory: Factory, breakdown: list[ScoreComponent]) -> list[str]:
    by = {c.criterion: c for c in breakdown}
    reasons = [by["process_fit"].note]
    if by["moq"].score < 1:
        reasons.append(by["moq"].note + " — MOQ above the order")
    if by["certifications"].score < 1:
        reasons.append(by["certifications"].note)
    reasons.append(("Capacity available: " if by["load"].score >= 0.5 else "Busy: ") + by["load"].note)
    reasons.append(("Fast: " if by["lead_time"].score >= 0.6 else "Slow: " if by["lead_time"].score < 0.4 else "") + by["lead_time"].note)
    pp = factory.past_performance
    if pp.orders_completed and not pp.no_data and pp.on_time_rate_pct is not None:
        reasons.append(f"{pp.on_time_rate_pct:.0f}% on-time over {pp.orders_completed} orders, {pp.defect_rate_pct}% defects")
    else:
        reasons.append("No order history on the network yet (no performance data)")
    reasons.append(f"Profile: {factory.archetype}")
    return reasons


def _match(rank: int, factory: Factory, breakdown: list[ScoreComponent], reasons: list[str]) -> FactoryMatch:
    return FactoryMatch(
        rank=rank,
        factory_id=factory.id,
        factory_name=factory.name,
        score=LabeledValue(value=total_score(breakdown), unit="score/100", label="fictional", source_or_assumption=FICTIONAL_SCORE_NOTE),
        score_breakdown=breakdown,
        reasons=reasons,
    )


def search_capacity(query: SearchCapacityQuery, limit: int = 8, today: date | None = None) -> list[FactoryMatch]:
    """Ranked factories for one (process, material, quantity, certifications, deadline) query.
    Factories that do not run the process are excluded. Ties break on factory id → fully deterministic."""
    scored = []
    for f in list_factories():
        bd = score_factory(f, query, today)
        if bd[0].score == 0:
            continue
        scored.append((f, bd))
    scored.sort(key=lambda x: (-total_score(x[1]), x[0].id))
    return [_match(i + 1, f, bd, _reasons(f, bd)) for i, (f, bd) in enumerate(scored[:limit])]


def rank_for_product(
    queries: list[SearchCapacityQuery], weights: list[float] | None = None, limit: int = 5, today: date | None = None
) -> list[FactoryMatch]:
    """Product-level ranking over several queries (one per process): each criterion is the weighted mean of
    the per-query scores, so process_fit becomes 'share of the product this factory can make in-house'."""
    if not queries:
        raise ValueError("at least one query is required")
    weights = weights or [1.0] * len(queries)
    wsum = sum(weights)
    ranked = []
    for f in list_factories():
        per_q = [score_factory(f, q, today) for q in queries]
        covered = [q.process for q, bd in zip(queries, per_q) if bd[0].score > 0]
        if not covered:
            continue
        missing = [q.process for q, bd in zip(queries, per_q) if bd[0].score == 0]
        breakdown = []
        for i, crit in enumerate(WEIGHTS):
            s = _clamp(sum(w * bd[i].score for w, bd in zip(weights, per_q)) / wsum)
            if crit == "process_fit":
                note = f"Covers {len(covered)}/{len(queries)} processes in-house ({', '.join(map(process_label, covered))})" + (
                    f"; would subcontract {', '.join(map(process_label, missing))}" if missing else ""
                )
            else:
                note = per_q[0][i].note
            breakdown.append(ScoreComponent(criterion=crit, score=s, weight=WEIGHTS[crit], note=note))
        ranked.append((f, breakdown))
    ranked.sort(key=lambda x: (-total_score(x[1]), x[0].id))
    return [_match(i + 1, f, bd, _reasons(f, bd)) for i, (f, bd) in enumerate(ranked[:limit])]


# --------------------------------------------------------------------------- tool 3: get_factory_profile


def get_factory_profile(factory_id: str) -> Factory:
    """Profile, capacity, audit notes and past performance — all fictional."""
    return _require_factory(factory_id)


# --------------------------------------------------------------------------- tool 4: request_quote


def request_quote(
    factory_id: str,
    factory_pack_id: str,
    quantities: list[int],
    project_id: str = "external",
    product_name: str | None = None,
) -> str:
    """Send an RFQ (with a Factory Pack reference) to one factory. Returns rfq_id."""
    _require_factory(factory_id)
    if not quantities:
        raise ValueError("quantities must not be empty")
    rfq = RFQ(
        id=_new_id("rfq"),
        project_id=project_id,
        factory_id=factory_id,
        factory_pack_id=factory_pack_id,
        quantities=sorted(set(int(q) for q in quantities)),
    )
    with _conn() as con:
        _save_rfq(con, rfq, product_name or f"Factory Pack {factory_pack_id}")
    return rfq.id


# --------------------------------------------------------------------------- tool 5: submit_quote


def _tiers(unit_prices: dict[int, float] | list[QuoteTier] | list[dict]) -> list[QuoteTier]:
    if isinstance(unit_prices, dict):
        return [QuoteTier(quantity=int(q), unit_price_usd=round(float(p), 2)) for q, p in sorted(unit_prices.items(), key=lambda x: int(x[0]))]
    return sorted((QuoteTier.model_validate(t) for t in unit_prices), key=lambda t: t.quantity)


def submit_quote(
    rfq_id: str,
    unit_prices: dict[int, float] | list[QuoteTier] | list[dict],
    tooling_usd: float,
    moq: int,
    lead_time_days: int,
    payment_terms: str,
    exceptions: list[str] | None = None,
) -> str:
    """Factory side: answer an RFQ. Each call creates a new version; older open versions become superseded."""
    rfq = get_rfq(rfq_id)
    if rfq.status == RFQStatus.accepted:
        raise ValueError(f"rfq {rfq_id} is already accepted")
    prev = list_quotes(rfq_id)
    q = Quote(
        id=_new_id("qt"),
        rfq_id=rfq_id,
        factory_id=rfq.factory_id,
        version=(prev[-1].version + 1) if prev else 1,
        tiers=_tiers(unit_prices),
        tooling_usd=round(float(tooling_usd), 2),
        moq=int(moq),
        lead_time_days=int(lead_time_days),
        payment_terms=payment_terms,
        exceptions=exceptions or [],
    )
    with _conn() as con:
        for old in prev:
            if old.status in (QuoteStatus.submitted, QuoteStatus.countered):
                old.status = QuoteStatus.superseded
                _save_quote(con, old)
        _save_quote(con, q)
        rfq.status = RFQStatus.quoted
        _save_rfq(con, rfq)
    return q.id


# --------------------------------------------------------------------------- tool 6: counter_offer

COUNTER_KEYS = {"unit_price_pct", "tiers", "tooling_usd", "moq", "lead_time_days", "payment_terms"}


def counter_offer(quote_id: str, proposed_changes: dict[str, Any], rationale: str) -> Quote:
    """Platform side: propose changes on a quote. Creates a new version (status `countered`) carrying the
    proposal; the previous version is superseded. The rationale travels in the caller's transcript. Keys: unit_price_pct (e.g. -5 → all tiers −5 %), tiers,
    tooling_usd, moq, lead_time_days, payment_terms."""
    base = get_quote(quote_id)
    if base.status in (QuoteStatus.accepted, QuoteStatus.rejected):
        raise ValueError(f"quote {quote_id} is {base.status}")
    unknown = set(proposed_changes) - COUNTER_KEYS
    if unknown:
        raise ValueError(f"unknown proposed_changes keys: {sorted(unknown)} (allowed: {sorted(COUNTER_KEYS)})")
    tiers = base.tiers
    if "tiers" in proposed_changes:
        tiers = _tiers(proposed_changes["tiers"])
    elif "unit_price_pct" in proposed_changes:
        k = 1 + float(proposed_changes["unit_price_pct"]) / 100
        tiers = [QuoteTier(quantity=t.quantity, unit_price_usd=round(t.unit_price_usd * k, 2)) for t in base.tiers]
    latest = list_quotes(base.rfq_id)[-1]
    new = Quote(
        id=_new_id("qt"),
        rfq_id=base.rfq_id,
        factory_id=base.factory_id,
        version=latest.version + 1,
        tiers=tiers,
        tooling_usd=round(float(proposed_changes.get("tooling_usd", base.tooling_usd)), 2),
        moq=int(proposed_changes.get("moq", base.moq)),
        lead_time_days=int(proposed_changes.get("lead_time_days", base.lead_time_days)),
        payment_terms=str(proposed_changes.get("payment_terms", base.payment_terms)),
        exceptions=base.exceptions,
        status=QuoteStatus.countered,
    )
    with _conn() as con:
        for old in list_quotes(base.rfq_id):
            if old.status in (QuoteStatus.submitted, QuoteStatus.countered):
                old.status = QuoteStatus.superseded
                _save_quote(con, old)
        _save_quote(con, new)
    return new


# --------------------------------------------------------------------------- tool 7: accept_quote


def accept_quote(quote_id: str) -> OrderDraft:
    """After user approval: accept one quote version → order draft. Other open versions on that RFQ are rejected."""
    q = get_quote(quote_id)
    rfq = get_rfq(q.rfq_id)
    factory = _require_factory(q.factory_id)
    with _conn() as con:
        for other in list_quotes(q.rfq_id):
            if other.id != q.id and other.status in (QuoteStatus.submitted, QuoteStatus.countered):
                other.status = QuoteStatus.rejected
                _save_quote(con, other)
        q.status = QuoteStatus.accepted
        _save_quote(con, q)
        rfq.status = RFQStatus.accepted
        _save_rfq(con, rfq)
        order = OrderDraft(
            order_id=_new_id("po"),
            quote_id=q.id,
            rfq_id=q.rfq_id,
            factory_id=q.factory_id,
            factory_name=factory.name,
            tiers=q.tiers,
            tooling_usd=q.tooling_usd,
            moq=q.moq,
            lead_time_days=q.lead_time_days,
            payment_terms=q.payment_terms,
        )
        con.execute("INSERT INTO order_draft VALUES (?, ?, ?)", (order.order_id, q.id, order.model_dump_json()))
    return order


# --------------------------------------------------------------------------- provider object


class FactoryNetwork:
    """Object handed to the API's factory portal (`@provider("network")`)."""

    list_factories = staticmethod(list_factories)
    get_factory = staticmethod(get_factory)
    list_rfqs = staticmethod(list_rfqs)


TOOL_NAMES = [
    "register_capacity",
    "search_capacity",
    "get_factory_profile",
    "request_quote",
    "submit_quote",
    "counter_offer",
    "accept_quote",
]

__all__ = TOOL_NAMES + [
    "FactoryNetwork",
    "NotFoundError",
    "OrderDraft",
    "WEIGHTS",
    "get_factory",
    "get_quote",
    "get_rfq",
    "list_factories",
    "list_quotes",
    "list_rfqs",
    "rank_for_product",
    "reset",
    "utcnow",
]
