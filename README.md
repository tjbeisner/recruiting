# Recruit Database (Streamlit starter)

A password-protected database of basketball recruits with add, edit, delete,
search/filter, and CSV export. Data is stored in a local SQLite file (`recruits.db`).

## Run it on your computer

```bash
pip install -r requirements.txt
streamlit run app.py
```

It opens at http://localhost:8501.

## Set the password

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and change
`APP_PASSWORD`. Everyone you share the app with uses that one password. If no
password is set, the app runs unlocked and shows a warning in the sidebar.

## Put it online for coaches (Streamlit Community Cloud, free)

1. Push this folder to a GitHub repo (the `.gitignore` keeps the database and
   your real password out of it).
2. Go to https://share.streamlit.io, click **Create app**, pick the repo, and set
   the main file to `app.py`.
3. In **Advanced settings > Secrets**, paste `APP_PASSWORD = "your-password"`.
4. Deploy and send coaches the URL and password.

**Important:** Community Cloud does not keep files between restarts, so the SQLite
database will be wiped whenever the app sleeps or redeploys. That is fine for
trying things out, but before coaches rely on it, switch storage to a hosted
database such as Google Sheets or Supabase (free Postgres). Only the
`get_conn` / `load_recruits` / `add_recruit` / `update_recruit` /
`delete_recruit` functions in `app.py` need to change.

## Where to customize

- Dropdown options: `POSITIONS` and `EVALUATIONS` at the top of `app.py`.
- New fields: add a column in `init_db`, add it to `FIELDS`, `COLUMN_LABELS`, and
  `recruit_form`. (Delete `recruits.db` after changing the table while testing.)
- Height is entered as feet + inches and stored as total inches, so it sorts correctly.
