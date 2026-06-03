# DGVCL Estimate Portal — Deployment Guide

## Step 1 — Create a new free PythonAnywhere account
- Go to https://www.pythonanywhere.com/registration/register/beginner/
- Pick a username (e.g. dgvcl or shreejielectricals2)
- Your app will be at: yourusername.pythonanywhere.com

## Step 2 — Upload the project
In PythonAnywhere → Files tab:
- Create a folder: /home/yourusername/dgvcl_app
- Upload all files from this zip into that folder
- Make sure templates/ folder is uploaded too

## Step 3 — Install dependencies
In PythonAnywhere → Bash console:
```
cd ~/dgvcl_app
pip3.10 install --user flask requests openpyxl werkzeug
```

## Step 4 — Create the Web App
- PythonAnywhere → Web tab → Add a new web app
- Choose: Manual configuration → Python 3.10
- WSGI file path will be shown (e.g. /var/www/yourusername_pythonanywhere_com_wsgi.py)
- Open that file and replace its contents with the contents of wsgi.py
  (remember to change 'yourusername' to your actual username)

## Step 5 — Reload and test
- Click Reload in the Web tab
- Visit yourusername.pythonanywhere.com
- Login with: admin / admin123
- CHANGE THE PASSWORD immediately in Users → delete admin → add new admin

## Step 6 — Connect Supabase (recommended for data safety)
1. Go to https://supabase.com → New project (free)
2. In DGVCL portal → Cloud / DB → Show SQL Setup Script
3. Copy the SQL → paste in Supabase SQL Editor → Run
4. In DGVCL portal → Cloud / DB → enter your Supabase URL + Secret key → Save
5. Click Test Connection → Push Local → Supabase

## Step 7 — Keep free account alive
PythonAnywhere free accounts are disabled after 3 months of inactivity.
Visit https://www.pythonanywhere.com every month and click "Run" in the Web tab.
Or set a phone reminder.

## Default Login
Username: admin
Password: admin123
(change immediately after first login)

## File Structure
dgvcl_app/
├── app.py              — Main Flask app (all routes)
├── database.py         — SQLite schema + sync helpers
├── supabase_api.py     — Supabase REST client
├── config_loader.py    — Reads config.xlsx for Supabase keys
├── wsgi.py             — PythonAnywhere WSGI entry point
├── requirements.txt    — Python dependencies
├── dgvcl.db            — Created automatically on first run
├── config.xlsx         — Created when you save Supabase keys
└── templates/
    ├── base.html           — Dark navy theme, sidebar
    ├── login.html          — Standalone login page
    ├── dashboard.html      — KPIs + chart + recent estimates
    ├── divisions.html      — Division cards
    ├── parties.html        — Party cards + add modal
    ├── estimates.html      — Entry form + filtered table
    ├── estimate_form.html  — Edit estimate
    ├── party_form.html     — Edit party
    ├── reports.html        — Analytics with period chart
    ├── users.html          — User management
    └── cloud_settings.html — Supabase connect + SQL script
