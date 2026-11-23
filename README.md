# OneGov PH

Flask + SQLAlchemy application for the OneGov PH government-service portal.
The database layer supports local XAMPP/MySQL development and MySQL-compatible
TiDB Cloud deployment through environment variables.

## 1. Install dependencies

```bash
cd OneGov-PH
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`PyMySQL` is the database driver (`mysql+pymysql`).

## 2. Configure `.env`

Copy the template and fill in your own values. Never commit `.env`.

```bash
cp .env.example .env
```

### Local XAMPP / MySQL

```dotenv
DATABASE_MODE=local
DATABASE_URL=mysql+pymysql://root:@localhost/onegov_ph
```

Start MySQL in XAMPP before running the app or migration.

### TiDB Cloud

```dotenv
DATABASE_MODE=tidb
DB_HOST=gateway01.<region>.prod.aws.tidbcloud.com
DB_PORT=4000
DB_USER=<your-tidb-user>
DB_PASSWORD=<your-tidb-password>
DB_NAME=onegov_ph

DB_SSL=true
# Point this at the CA bundle downloaded from the TiDB Cloud console.
DB_SSL_CA=/absolute/path/to/isrgrootx1.pem
DB_SSL_VERIFY_CERT=true
DB_SSL_VERIFY_IDENTITY=true
DB_POOL_RECYCLE=280
```

`DATABASE_MODE=auto` (the default) uses the `DB_*` values when `DB_HOST` is
set and falls back to `DATABASE_URL` otherwise. Use `DATABASE_MODE=local` to
force XAMPP even when TiDB values are present.

TiDB Cloud requires TLS. Download the CA certificate from the cluster's
**Connect** dialog, save it locally, and set `DB_SSL_CA` to that absolute path.
If you leave `DB_SSL_CA` empty, the connection is still encrypted but the
server certificate is not verified (development only).

Credentials must stay in `.env`. `.env` is already listed in `.gitignore`.

## 3. Create tables and reference data

The migration script is non-destructive. It never drops or truncates tables and
never deletes rows. It creates only missing tables and can be run repeatedly.

```bash
# Verify the connection and create any missing tables
python database/migrate.py

# Create missing tables and load department/service reference data
python database/migrate.py --seed

# Verify only, without creating anything
python database/migrate.py --check
```

`database/seed.sql` uses `INSERT IGNORE`, so running it again does not create
duplicates. It contains departments and the eight in-scope services only:

1. PSA Birth Certificate
2. PSA CENOMAR
3. PhilSys National ID (registration assistance)
4. NBI Clearance (application monitoring)
5. SSS SS Number Registration
6. LGU Barangay Clearance
7. LGU Certificate of Residency
8. LGU Senior Citizen ID

It does **not** insert citizen/staff accounts, applications, payments,
appointments, notifications, passport services, or Pag-IBIG services.

### Alternative: run SQL manually

`database/schema.sql` contains the same tables in dependency order using
`CREATE TABLE IF NOT EXISTS`, and is compatible with the TiDB SQL editor.
For a normal deployment, prefer `python database/migrate.py --seed` so the
tables are built from the SQLAlchemy models.

## 4. Verify tables in TiDB Cloud

Open the TiDB Cloud SQL editor (or connect with `mysql`/your SQL client) and run:

```sql
USE onegov_ph;
SHOW TABLES;
```

Expected tables:

```
account_activity_logs
account_requests
application_requirements
application_tracking
applications
audit_logs
departments
email_otps
nbi_appointments
notifications
passport_appointments
payments
services
user_sessions
users
```

You can also verify reference data:

```sql
SELECT department_name, department_status FROM departments ORDER BY department_name;
SELECT service_name, processing_fee, service_status FROM services ORDER BY service_name;
```

## 5. Run the Flask application

```bash
python app.py
```

The app listens on `http://127.0.0.1:5001` (port 5000 is used by macOS AirPlay).
On startup it checks the configured database and creates any missing tables
with SQLAlchemy `metadata.create_all(..., checkfirst=True)`. It never drops or
truncates existing tables.

## Troubleshooting

- **`Table 'onegov_ph.users' doesn't exist`** — run `python database/migrate.py`
  before starting the app or running migration SQL.
- **TiDB TLS / certificate errors** — set `DB_SSL_CA` to the downloaded CA file
  and keep `DB_SSL_VERIFY_CERT=true`. For quick testing, `DB_SSL_VERIFY_CERT=false`
  encrypts without verification.
- **Wrong database is used** — set `DATABASE_MODE=local` or `DATABASE_MODE=tidb`
  explicitly instead of relying on `auto`.
- **Migration reports missing tables** — check the database user has permission
  to create tables in `onegov_ph`, then run `python database/migrate.py` again.
