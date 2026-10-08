"""Kestrel Valley CU practice APIs (runs on your own computer).

Start it:      python mockapi/server.py
Then open:     http://127.0.0.1:8000/docs

Three fake systems, shaped like the real tools a compliance team uses:
  1. FormsHub   - an OData feed of web complaint form entries (like Cognito Forms)
  2. GRC        - a table API for compliance issues (like ServiceNow)
  3. Boards     - a GraphQL API for a remediation task board (like monday.com)

Options:
  --port 8000      change the port
  --chaos          make some requests fail on purpose (Lab 2.4)
  --day 1          which day of GRC data to serve (1, 2 or 3). You can also POST /admin/day/2
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import operator
import re
import secrets
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import strawberry
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

FORMS_TOKEN = "kvcu-forms-demo-token"
GRC_USER, GRC_PASSWORD = "svc_dataeng", "Kestrel!2026"
BOARD_TOKEN = "kvcu-board-demo-token"

FORMS = json.load(gzip.open(DATA / "forms_entries.json.gz", "rt", encoding="utf-8"))
GRC = json.load(gzip.open(DATA / "grc.json.gz", "rt", encoding="utf-8"))
BOARD = json.load(gzip.open(DATA / "board.json.gz", "rt", encoding="utf-8"))
BRANCHES = [
    {"code": "01", "name": "Millbrook Main", "region": "North"},
    {"code": "02", "name": "Riverbend", "region": "North"},
    {"code": "03", "name": "Stonegate", "region": "South"},
    {"code": "04", "name": "Orchard Hill", "region": "South"},
    {"code": "05", "name": "Harbor Point", "region": "East"},
    {"code": "06", "name": "Cedar Falls", "region": "West"},
    {"code": "07", "name": "Westfield", "region": "West"},
    {"code": "08", "name": "Northgate", "region": "North"},
    {"code": "99", "name": "Digital Branch", "region": "Digital"},
]

STATE = {"day": 1, "chaos": False, "attempts": {}}

app = FastAPI(
    title="Kestrel Valley CU practice APIs",
    description="Fake data for learning. Tokens: see the README or the banner printed at startup.",
)


@app.get("/health")
def health():
    return {"status": "ok", "grc_day": STATE["day"], "chaos": STATE["chaos"]}


@app.get("/api/branches")
def branches():
    """No login needed. Good first API call."""
    return {"count": len(BRANCHES), "branches": BRANCHES}


@app.post("/admin/day/{day}")
def set_day(day: int):
    if day not in (1, 2, 3):
        raise HTTPException(400, "day must be 1, 2 or 3")
    STATE["day"] = day
    return {"grc_day": day, "as_of": GRC["snapshots"][str(day)]["as_of"]}


@app.post("/admin/chaos/{on}")
def set_chaos(on: str):
    STATE["chaos"] = on.lower() in ("1", "true", "on", "yes")
    STATE["attempts"] = {}
    return {"chaos": STATE["chaos"]}


@app.post("/admin/reset")
def reset():
    STATE["attempts"] = {}
    STATE["day"] = 1
    return {"reset": True}


# ------------------------------------------------------------------ 1. FormsHub OData
def _forms_auth(request: Request):
    tok = request.query_params.get("access_token")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
    if tok != FORMS_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid access token. Send ?access_token=... or 'Authorization: Bearer ...'.",
        )


def _get_path(obj, path):
    for part in path.split("/"):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


ODATA_OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "ge": operator.ge,
    "gt": operator.gt,
    "le": operator.le,
    "lt": operator.lt,
}
FILTER_RE = re.compile(r"^\s*([\w/]+)\s+(eq|ne|ge|gt|le|lt)\s+('([^']*)'|[\w:.\-+]+|null)\s*$", re.I)


def _apply_filter(rows, expr):
    if not expr:
        return rows
    parts = re.split(r"\s+and\s+", expr, flags=re.I)
    conds = []
    for p in parts:
        m = FILTER_RE.match(p)
        if not m:
            raise HTTPException(
                400, f"Unsupported $filter clause: {p!r}. Try: Entry/DateSubmitted ge 2026-01-01T00:00:00Z"
            )
        field, op, raw, quoted = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        val = None if raw.lower() == "null" else (quoted if quoted is not None else raw)
        conds.append((field, op, val))

    def ok(r):
        for field, op, val in conds:
            x = _get_path(r, field)
            if val is None:
                if (op == "eq" and x is not None) or (op == "ne" and x is None):
                    return False
                continue
            if x is None:
                return False
            xs, vs = str(x), str(val)
            if isinstance(x, (int, float)) and not isinstance(x, bool):
                try:
                    xs, vs = float(x), float(val)
                except ValueError:
                    pass
            if not ODATA_OPS[op](xs, vs):
                return False
        return True

    return [r for r in rows if ok(r)]


def _chaos(key: str):
    """Deterministic failures for Lab 2.4. Same page fails the same way every run."""
    if not STATE["chaos"]:
        return None
    n = STATE["attempts"].get(key, 0) + 1
    STATE["attempts"][key] = n
    plan = {"skip=300": [503], "skip=700": [429], "skip=1200": [500, 500], "skip=1500": ["slow"]}
    fails = plan.get(key, [])
    if n <= len(fails):
        f = fails[n - 1]
        if f == "slow":
            time.sleep(8)
            return None
        if f == 429:
            return JSONResponse(
                {"error": "Too many requests. Slow down."}, status_code=429, headers={"Retry-After": "2"}
            )
        return JSONResponse({"error": "Server hiccup. Try again."}, status_code=f)
    return None


@app.get("/odata/Forms(12)/Entries", dependencies=[Depends(_forms_auth)])
@app.get("/odata/Forms(12)/Entries/", dependencies=[Depends(_forms_auth)], include_in_schema=False)
def odata_entries(request: Request):
    """OData feed of complaint form entries. Supports $top, $skip, $count, $select, $filter, $orderby."""
    q = request.query_params
    try:
        top = int(q.get("$top", 100))
        skip = int(q.get("$skip", 0))
    except ValueError as err:
        raise HTTPException(400, "$top and $skip must be whole numbers") from err
    page = max(1, min(top, 250))
    fail = _chaos(f"skip={skip}")
    if fail is not None:
        return fail
    rows = _apply_filter(FORMS, q.get("$filter"))
    order = q.get("$orderby", "Entry/Number asc")
    fld, _, direction = order.partition(" ")
    rows = sorted(
        rows, key=lambda r: (_get_path(r, fld) is None, _get_path(r, fld) or 0), reverse=direction.lower() == "desc"
    )
    total = len(rows)
    chunk = rows[skip : skip + page]
    sel = q.get("$select")
    if sel:
        keep = [s.strip() for s in sel.split(",") if s.strip()]
        chunk = [{k: r.get(k) for k in keep} for r in chunk]
    body = {"@odata.context": str(request.base_url) + "odata/$metadata#Entries", "value": chunk}
    if q.get("$count", "").lower() == "true":
        body["@odata.count"] = total
    if skip + page < total:
        params = {k: v for k, v in q.items() if k not in ("$skip",)}
        params["$skip"] = skip + page
        params["$top"] = page
        body["@odata.nextLink"] = str(request.base_url).rstrip("/") + request.url.path + "?" + urlencode(params)
    return body


# ------------------------------------------------------------------ 2. GRC table API (ServiceNow-style)
basic = HTTPBasic()


def _grc_auth(creds: HTTPBasicCredentials = Depends(basic)):
    ok = secrets.compare_digest(creds.username, GRC_USER) and secrets.compare_digest(creds.password, GRC_PASSWORD)
    if not ok:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {"message": "User Not Authenticated", "detail": "Required to provide Auth information"},
                "status": "failure",
            },
            headers={"WWW-Authenticate": "Basic"},
        )


REF_FIELDS = {"assigned_to": "sys_user"}
CHOICE_FIELDS = {"state": "states", "priority": "priorities"}


def _display(row, field, mode, base):
    v = row.get(field, "")
    if field in REF_FIELDS:
        if v == "":
            return ""
        link = f"{base}api/now/table/{REF_FIELDS[field]}/{v}"
        name = next((u["name"] for u in GRC["users"] if u["sys_id"] == v), "")
        if mode == "true":
            return {"display_value": name, "link": link}
        if mode == "all":
            return {"display_value": name, "value": v, "link": link}
        return {"link": link, "value": v}
    if field in CHOICE_FIELDS:
        label = GRC[CHOICE_FIELDS[field]].get(v, v)
        if mode == "true":
            return label
        if mode == "all":
            return {"display_value": label, "value": v}
        return v
    if field == "u_regulation":
        label = GRC["regulations"].get(v, v)
        return label if mode == "true" else ({"display_value": label, "value": v} if mode == "all" else v)
    if mode == "all":
        return {"display_value": v, "value": v}
    return v


SN_OPS = {
    "=": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "LIKE": lambda x, v: v.lower() in x.lower(),
    "STARTSWITH": lambda x, v: x.lower().startswith(v.lower()),
}
COND_RE = re.compile(r"^(\w+)(>=|<=|!=|>|<|=|LIKE|STARTSWITH)(.*)$")


def _sn_query(rows, query):
    if not query:
        return rows, None
    order = None
    conds = []
    for part in query.split("^"):
        if not part:
            continue
        if part.startswith("ORDERBYDESC"):
            order = (part[len("ORDERBYDESC") :], True)
            continue
        if part.startswith("ORDERBY"):
            order = (part[len("ORDERBY") :], False)
            continue
        m = COND_RE.match(part)
        if not m:
            raise HTTPException(400, f"Unsupported sysparm_query part: {part!r}")
        conds.append(m.groups())

    def ok(r):
        for f, op, v in conds:
            x = str(r.get(f, ""))
            if not SN_OPS[op](x, v):
                return False
        return True

    return [r for r in rows if ok(r)], order


@app.get("/api/now/table/grc_issue", dependencies=[Depends(_grc_auth)])
def grc_issues(request: Request, response: Response):
    """ServiceNow-style table API. Everything comes back as strings, like the real thing."""
    q = request.query_params
    rows = GRC["snapshots"][str(STATE["day"])]["rows"]
    rows, order = _sn_query(rows, q.get("sysparm_query", ""))
    if order:
        rows = sorted(rows, key=lambda r: r.get(order[0], ""), reverse=order[1])
    else:
        rows = sorted(rows, key=lambda r: r["sys_id"])
    try:
        limit = min(int(q.get("sysparm_limit", 100)), 500)
        offset = int(q.get("sysparm_offset", 0))
    except ValueError as err:
        raise HTTPException(400, "sysparm_limit and sysparm_offset must be numbers") from err
    total = len(rows)
    chunk = rows[offset : offset + limit]
    mode = q.get("sysparm_display_value", "false").lower()
    fields = [f for f in q.get("sysparm_fields", "").split(",") if f] or list(rows[0].keys() if rows else [])
    base = str(request.base_url)
    out = [{f: _display(r, f, mode, base) for f in fields} for r in chunk]
    response.headers["X-Total-Count"] = str(total)
    links = []
    path = base.rstrip("/") + request.url.path

    def mk(off):
        p = dict(q)
        p["sysparm_offset"] = off
        p["sysparm_limit"] = limit
        return path + "?" + urlencode(p)

    links.append(f'<{mk(0)}>;rel="first"')
    if offset + limit < total:
        links.append(f'<{mk(offset + limit)}>;rel="next"')
    if offset > 0:
        links.append(f'<{mk(max(0, offset - limit))}>;rel="prev"')
    links.append(f'<{mk(max(0, (total - 1) // limit * limit))}>;rel="last"')
    response.headers["Link"] = ",".join(links)
    return {"result": out}


@app.get("/api/now/table/sys_user", dependencies=[Depends(_grc_auth)])
def grc_users():
    return {"result": [{"sys_id": u["sys_id"], "name": u["name"], "email": u["email"]} for u in GRC["users"]]}


# ------------------------------------------------------------------ 3. Boards GraphQL (monday-style)
USERS = {u["id"]: u for u in BOARD["users"]}
COLS = {c["id"]: c for c in BOARD["columns"]}
GROUPS = {g["id"]: g for g in BOARD["groups"]}


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: Optional[str]


@strawberry.type
class Column:
    id: strawberry.ID
    title: str
    type: str


@strawberry.type
class Group:
    id: strawberry.ID
    title: str


@strawberry.type
class ColumnValue:
    id: strawberry.ID
    type: str
    text: Optional[str]
    value: Optional[str]

    @strawberry.field
    def column(self) -> Column:
        c = COLS[self.id]
        return Column(id=c["id"], title=c["title"], type=c["type"])


@strawberry.type
class Update:
    id: strawberry.ID
    body: str
    text_body: Optional[str]
    created_at: Optional[str]
    creator_id: strawberry.Private[int]

    @strawberry.field
    def creator(self) -> Optional[User]:
        u = USERS.get(self.creator_id)
        return User(id=str(u["id"]), name=u["name"], email=u["email"]) if u else None


@strawberry.type
class Item:
    id: strawberry.ID
    name: str
    state: str
    created_at: Optional[str]
    updated_at: Optional[str]
    raw: strawberry.Private[dict]

    @strawberry.field
    def group(self) -> Group:
        g = GROUPS[self.raw["group_id"]]
        return Group(id=g["id"], title=g["title"])

    @strawberry.field
    def column_values(self, ids: Optional[list[str]] = None) -> list[ColumnValue]:
        cvs = self.raw["column_values"]
        if ids:
            cvs = [c for c in cvs if c["id"] in ids]
        return [ColumnValue(id=c["id"], type=c["type"], text=c["text"], value=c["value"]) for c in cvs]

    @strawberry.field
    def updates(self, limit: int = 25) -> list[Update]:
        return [
            Update(
                id=u["id"],
                body=u["body"],
                text_body=u["text_body"],
                created_at=u["created_at"],
                creator_id=u["creator_id"],
            )
            for u in self.raw["updates"][:limit]
        ]


@strawberry.type
class ItemsPage:
    cursor: Optional[str]
    items: list[Item]


def _page(offset: int, limit: int) -> ItemsPage:
    if limit > 500:
        raise ValueError("limit cannot be more than 500")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = BOARD["items"][offset : offset + limit]
    nxt = offset + limit
    cursor = (
        base64.urlsafe_b64encode(f"{BOARD['id']}:{nxt}:{int(time.time())}".encode()).decode()
        if nxt < len(BOARD["items"])
        else None
    )
    return ItemsPage(
        cursor=cursor,
        items=[
            Item(
                id=r["id"],
                name=r["name"],
                state=r["state"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                raw=r,
            )
            for r in rows
        ],
    )


@strawberry.type
class Board:
    id: strawberry.ID
    name: str
    items_count: int

    @strawberry.field
    def groups(self) -> list[Group]:
        return [Group(id=g["id"], title=g["title"]) for g in BOARD["groups"]]

    @strawberry.field
    def columns(self) -> list[Column]:
        return [Column(id=c["id"], title=c["title"], type=c["type"]) for c in BOARD["columns"]]

    @strawberry.field
    def items_page(self, limit: int = 25, cursor: Optional[str] = None) -> ItemsPage:
        off = 0
        if cursor:
            off = _decode_cursor(cursor)
        return _page(off, limit)


def _decode_cursor(cursor: str) -> int:
    try:
        board_id, off, _ = base64.urlsafe_b64decode(cursor.encode()).decode().split(":")
        return int(off)
    except Exception as err:
        raise ValueError("CursorException: cursor is not valid") from err


@strawberry.type
class Complexity:
    before: int
    query: int
    after: int
    reset_in_x_seconds: int


@strawberry.type
class Query:
    @strawberry.field
    def boards(self, ids: Optional[list[strawberry.ID]] = None) -> list[Board]:
        if ids and BOARD["id"] not in [str(i) for i in ids]:
            return []
        return [Board(id=BOARD["id"], name=BOARD["name"], items_count=len(BOARD["items"]))]

    @strawberry.field
    def next_items_page(self, cursor: str, limit: int = 25) -> ItemsPage:
        return _page(_decode_cursor(cursor), limit)

    @strawberry.field
    def users(self) -> list[User]:
        return [User(id=str(u["id"]), name=u["name"], email=u["email"]) for u in BOARD["users"]]

    @strawberry.field
    def complexity(self) -> Complexity:
        return Complexity(before=10_000_000, query=1000, after=9_999_000, reset_in_x_seconds=60)


async def _board_context(request: Request):
    tok = request.headers.get("authorization", "")
    if tok.lower().startswith("bearer "):
        tok = tok[7:]
    if tok.strip() != BOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Not Authenticated: send your token in the Authorization header")
    return {}


schema = strawberry.Schema(query=Query, config=StrawberryConfig(auto_camel_case=False))
app.include_router(GraphQLRouter(schema, context_getter=_board_context, graphql_ide="graphiql"), prefix="/v2")


def main():
    ap = argparse.ArgumentParser(description="Kestrel Valley CU practice APIs")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--chaos", action="store_true", help="make some requests fail on purpose (Lab 2.4)")
    ap.add_argument("--day", type=int, default=1, choices=[1, 2, 3], help="GRC data day")
    a = ap.parse_args()
    STATE["chaos"] = a.chaos
    STATE["day"] = a.day
    print("\n  Kestrel Valley CU practice APIs")
    print(f"  Docs:       http://{a.host}:{a.port}/docs")
    print(f"  FormsHub:   GET  /odata/Forms(12)/Entries      token: {FORMS_TOKEN}")
    print(f"  GRC:        GET  /api/now/table/grc_issue       user: {GRC_USER}  password: {GRC_PASSWORD}")
    print(f"  Boards:     POST /v2  (GraphQL)                 token: {BOARD_TOKEN}")
    print(f"  GRC day: {a.day}   chaos: {'ON' if a.chaos else 'off'}   Stop with Ctrl+C\n")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
