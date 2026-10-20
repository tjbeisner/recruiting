"""Basketball Recruit Database - a starter Streamlit app.

Run locally:  streamlit run app.py
"""
import hmac
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "recruits.db"

POSITIONS = ["Point Guard", "Guard", "Wing", "Forward", "Center"]
CLASSES = ["2027", "2028", "2029", "JuCo", "NCAA", "D2", "International"]
EVALUATIONS = ["HM+", "HM", "HM-", "MM+", "MM", "MM-", "LM+", "LM", "REJECT"]

COLUMN_LABELS = {
    "id": "ID",
    "first_name": "First Name",
    "last_name": "Last Name",
    "position": "Position",
    "class_category": "Class/Category",
    "current_school": "Current School",
    "height": "Height",
    "player_contact": "Player Contact",
    "agent_name": "Agent Name",
    "agent_contact": "Agent Contact",
    "evaluation": "Evaluation",
    "notes": "Notes",
    "updated_at": "Last Updated",
}

st.set_page_config(page_title="Recruit Database", page_icon="🏀", layout="wide")


# ---------- Password gate ----------
def check_password() -> bool:
    """Ask for the shared password stored in st.secrets["APP_PASSWORD"]."""
    try:
        expected = st.secrets.get("APP_PASSWORD")
    except Exception:  # no secrets file at all
        expected = None
    if not expected:
        st.sidebar.warning("No APP_PASSWORD set, so the app is unlocked. Set one before sharing.")
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("🏀 Recruit Database")
    pwd = st.text_input("Password", type="password")
    if pwd:
        if hmac.compare_digest(pwd, expected):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ---------- Database helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recruits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                position TEXT,
                class_category TEXT,
                current_school TEXT,
                height_inches INTEGER,
                player_contact TEXT,
                agent_name TEXT,
                agent_contact TEXT,
                evaluation TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Migration: add columns introduced after the first version
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(recruits)")}
        if "class_category" not in existing:
            conn.execute("ALTER TABLE recruits ADD COLUMN class_category TEXT")


def fmt_height(inches):
    if inches is None or pd.isna(inches) or inches == 0:
        return ""
    inches = int(inches)
    return f"{inches // 12}'{inches % 12}\""


def load_recruits() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM recruits ORDER BY last_name, first_name", conn)
    df["height"] = df["height_inches"].apply(fmt_height)
    return df


FIELDS = ["first_name", "last_name", "position", "class_category", "current_school", "height_inches",
          "player_contact", "agent_name", "agent_contact", "evaluation", "notes"]


def add_recruit(data: dict):
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO recruits ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
            [data[f] for f in FIELDS],
        )


def update_recruit(recruit_id: int, data: dict):
    with get_conn() as conn:
        conn.execute(
            f"UPDATE recruits SET {', '.join(f'{f} = ?' for f in FIELDS)}, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [data[f] for f in FIELDS] + [recruit_id],
        )


def parse_height(value):
    """Turn 6'5", 6-5, 6 5, or 77 (inches) into total inches."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace('"', "").replace("’", "'")
    if not text:
        return None
    for sep in ("'", "-", " "):
        if sep in text:
            ft, _, inch = text.partition(sep)
            try:
                return int(ft) * 12 + int(inch.strip() or 0)
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None


def import_recruits(df: pd.DataFrame) -> tuple[int, int]:
    """Add rows from an uploaded CSV. Skips players whose name is already in the database."""
    label_to_field = {v.lower(): k for k, v in COLUMN_LABELS.items()}
    df = df.rename(columns=lambda c: label_to_field.get(str(c).strip().lower(), str(c).strip().lower()))
    if "height" in df.columns and "height_inches" not in df.columns:
        df["height_inches"] = df["height"].apply(parse_height)

    with get_conn() as conn:
        existing = {(r["first_name"].lower(), r["last_name"].lower())
                    for r in conn.execute("SELECT first_name, last_name FROM recruits")}

    added = skipped = 0
    for _, row in df.iterrows():
        data = {}
        for f in FIELDS:
            v = row.get(f)
            data[f] = None if v is None or pd.isna(v) or str(v).strip() == "" else str(v).strip()
        if data["height_inches"] is not None:
            data["height_inches"] = parse_height(data["height_inches"])
        data["first_name"] = data["first_name"] or ""
        data["last_name"] = data["last_name"] or ""
        key = (data["first_name"].lower(), data["last_name"].lower())
        if key == ("", "") or key in existing:
            skipped += 1
            continue
        add_recruit(data)
        existing.add(key)
        added += 1
    return added, skipped


def delete_recruit(recruit_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM recruits WHERE id = ?", (recruit_id,))


# ---------- Shared form ----------
def recruit_form(key: str, existing: dict | None = None):
    """Render the recruit form. Returns a dict of values when submitted, else None."""
    e = existing or {}
    height = e.get("height_inches") or 0
    with st.form(key, clear_on_submit=existing is None):
        c1, c2 = st.columns(2)
        first_name = c1.text_input("First Name *", e.get("first_name", ""))
        last_name = c2.text_input("Last Name *", e.get("last_name", ""))

        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        pos_opts = [""] + POSITIONS
        position = c1.selectbox("Position", pos_opts,
                                index=pos_opts.index(e["position"]) if e.get("position") in POSITIONS else 0)
        current_school = c2.text_input("Current School", e.get("current_school") or "")
        class_opts = [""] + CLASSES
        class_category = st.selectbox("Class/Category", class_opts,
                                      index=class_opts.index(e["class_category"]) if e.get("class_category") in CLASSES else 0)
        feet = c3.number_input("Height (ft)", 0, 8, int(height) // 12, step=1)
        inches = c4.number_input("Height (in)", 0, 11, int(height) % 12, step=1)

        player_contact = st.text_input("Player Contact (phone / email)", e.get("player_contact") or "")
        c1, c2 = st.columns(2)
        agent_name = c1.text_input("Agent Name", e.get("agent_name") or "")
        agent_contact = c2.text_input("Agent Contact", e.get("agent_contact") or "")

        eval_opts = [""] + EVALUATIONS
        evaluation = st.selectbox("Evaluation", eval_opts,
                                  index=eval_opts.index(e["evaluation"]) if e.get("evaluation") in EVALUATIONS else 0)
        notes = st.text_area("Notes", e.get("notes") or "", height=120)

        submitted = st.form_submit_button("Save Recruit" if existing is None else "Update Recruit",
                                          type="primary")

    if not submitted:
        return None
    if not first_name.strip() or not last_name.strip():
        st.error("First and last name are required.")
        return None
    total = feet * 12 + inches
    return {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "position": position or None,
        "class_category": class_category or None,
        "current_school": current_school.strip() or None,
        "height_inches": total or None,
        "player_contact": player_contact.strip() or None,
        "agent_name": agent_name.strip() or None,
        "agent_contact": agent_contact.strip() or None,
        "evaluation": evaluation or None,
        "notes": notes.strip() or None,
    }


# ---------- Pages ----------
def browse_page():
    df = load_recruits()
    st.subheader(f"Recruits ({len(df)})")
    if df.empty:
        st.info("No recruits yet. Add one from the **Add Recruit** tab.")
        return

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search = c1.text_input("Search name, school, agent, or notes")
    pos_filter = c2.multiselect("Position", POSITIONS)
    class_filter = c3.multiselect("Class/Category", CLASSES)
    eval_filter = c4.multiselect("Evaluation", EVALUATIONS)

    filtered = df
    if search:
        s = search.lower()
        cols = ["first_name", "last_name", "current_school", "agent_name", "notes"]
        mask = filtered[cols].fillna("").apply(lambda col: col.str.lower().str.contains(s, regex=False)).any(axis=1)
        filtered = filtered[mask]
    if pos_filter:
        filtered = filtered[filtered["position"].isin(pos_filter)]
    if class_filter:
        filtered = filtered[filtered["class_category"].isin(class_filter)]
    if eval_filter:
        filtered = filtered[filtered["evaluation"].isin(eval_filter)]

    # Sort by evaluation tier (HM+ first), then name
    filtered = filtered.assign(
        _eval_rank=filtered["evaluation"].map({e: i for i, e in enumerate(EVALUATIONS)}).fillna(len(EVALUATIONS))
    ).sort_values(["_eval_rank", "last_name", "first_name"])

    display = filtered[list(COLUMN_LABELS)].rename(columns=COLUMN_LABELS)
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption(f"Showing {len(filtered)} of {len(df)}")

    st.download_button(
        "Download CSV",
        display.to_csv(index=False).encode("utf-8"),
        file_name="recruits.csv",
        mime="text/csv",
    )


def add_page():
    st.subheader("Add Recruit")
    if msg := st.session_state.pop("flash", None):
        st.success(msg)
    data = recruit_form("add_form")
    if data:
        add_recruit(data)
        st.session_state["flash"] = f"Added {data['first_name']} {data['last_name']}."
        st.rerun()  # refresh so the Browse tab shows the new recruit


def edit_page():
    st.subheader("Edit or Delete Recruit")
    df = load_recruits()
    if df.empty:
        st.info("No recruits to edit yet.")
        return

    options = {
        int(r.id): f"{r.last_name}, {r.first_name}" + (f" ({r.current_school})" if r.current_school else "")
        for r in df.itertuples()
    }
    recruit_id = st.selectbox("Choose a recruit", list(options), format_func=options.get)
    existing = df[df["id"] == recruit_id].iloc[0].to_dict()

    data = recruit_form(f"edit_form_{recruit_id}", existing)
    if data:
        update_recruit(recruit_id, data)
        st.success("Recruit updated.")
        st.rerun()

    with st.expander("Delete this recruit"):
        confirm = st.checkbox("Yes, permanently delete this recruit", key=f"confirm_{recruit_id}")
        if st.button("Delete", disabled=not confirm, key=f"delete_{recruit_id}"):
            delete_recruit(recruit_id)
            st.success("Recruit deleted.")
            st.rerun()


def import_page():
    st.subheader("Import from CSV")
    st.write(
        "Upload a CSV with column headers matching the field names (First Name, Last Name, "
        "Position, Class/Category, ...). Missing columns are fine. Players already in the "
        "database (same first and last name) are skipped. A CSV downloaded from the Browse tab "
        "can be re-imported here to restore your data."
    )
    if msg := st.session_state.pop("import_flash", None):
        st.success(msg)
    uploaded = st.file_uploader("CSV file", type="csv")
    if uploaded is None:
        return
    df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    st.dataframe(df, hide_index=True, width="stretch")
    if st.button(f"Import {len(df)} rows", type="primary"):
        added, skipped = import_recruits(df)
        st.session_state["import_flash"] = f"Imported {added} recruits ({skipped} skipped as duplicates or blank)."
        st.rerun()


# ---------- Main ----------
def main():
    if not check_password():
        st.stop()
    init_db()
    st.title("🏀 Recruit Database")
    tab_browse, tab_add, tab_edit, tab_import = st.tabs(["Browse", "Add Recruit", "Edit / Delete", "Import"])
    with tab_browse:
        browse_page()
    with tab_add:
        add_page()
    with tab_edit:
        edit_page()
    with tab_import:
        import_page()


main()
