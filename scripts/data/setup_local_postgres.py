"""
Local PostgreSQL Server Detection and Lifecycle Manager.

Detects and manages an existing PostgreSQL installation.
Credentials and connection parameters are derived exclusively from environment/configuration.
Automatic binary downloads are strictly removed and disabled.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

# Add backend directory to sys.path to access configuration
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

try:
    from app.config import settings
    DEFAULT_DB_URL = settings.DATABASE_URL
except Exception:
    DEFAULT_DB_URL = "postgresql+psycopg2://localhost:5432/smart_postal_db"


def get_target_db_url() -> str:
    """Retrieve database URL from environment or app configuration."""
    return os.environ.get("DATABASE_URL", DEFAULT_DB_URL)


def detect_postgres_bin() -> Path:
    """
    Detects existing PostgreSQL binary directory from environment or standard installation paths.
    Automatic binary download is strictly disabled.
    """
    # 1. Environment variable overrides
    for env_var in ["POSTGRES_BIN_PATH", "PG_BIN_DIR"]:
        custom_path = os.environ.get(env_var)
        if custom_path:
            p = Path(custom_path)
            if (p / "pg_ctl.exe").exists() or (p / "pg_ctl").exists() or (p / "postgres.exe").exists():
                return p

    # 2. System PATH
    for bin_name in ["pg_ctl", "postgres", "psql"]:
        which_path = shutil.which(bin_name)
        if which_path:
            return Path(which_path).resolve().parent

    # 3. Known user-space and program files installation directories
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    candidate_paths = [
        Path(local_app_data) / "Programs" / "PostgreSQL" / "pgsql" / "bin",
        Path(local_app_data) / "Programs" / "PostgreSQL" / "bin",
        Path(r"C:\Program Files\PostgreSQL") / "15" / "bin",
        Path(r"C:\Program Files\PostgreSQL") / "16" / "bin",
        Path(r"C:\Program Files\PostgreSQL") / "14" / "bin",
    ]
    for cand in candidate_paths:
        if (cand / "pg_ctl.exe").exists() or (cand / "postgres.exe").exists():
            return cand

    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    for cand in Path(prog_files).glob("PostgreSQL/*/bin"):
        if (cand / "pg_ctl.exe").exists() or (cand / "postgres.exe").exists():
            return cand

    raise RuntimeError(
        "PostgreSQL installation not detected. Automatic binary download is disabled.\n"
        "Please ensure PostgreSQL is installed and either set POSTGRES_BIN_PATH or ensure "
        "pg_ctl / postgres is in your system PATH."
    )


def get_postgres_data_dir() -> Path:
    """Retrieve cluster data directory from environment or standard user-space location."""
    if os.environ.get("POSTGRES_DATA_DIR"):
        return Path(os.environ["POSTGRES_DATA_DIR"])
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    return Path(local_app_data) / "Programs" / "PostgreSQL" / "data"


def init_cluster(pg_bin_dir: Path, data_dir: Path, target_url: str):
    """Initializes PostgreSQL cluster if data directory does not already exist."""
    if not (data_dir / "PG_VERSION").exists():
        print(f"Initializing PostgreSQL cluster at {data_dir}...")
        initdb_exe = pg_bin_dir / ("initdb.exe" if sys.platform == "win32" else "initdb")
        url_obj = make_url(target_url)
        username = url_obj.username or os.environ.get("POSTGRES_USER", "postgres")
        password = url_obj.password or os.environ.get("POSTGRES_PASSWORD", "")

        cmd = [
            str(initdb_exe),
            "-D", str(data_dir),
            "-U", username,
            "-A", "scram-sha-256" if password else "trust",
            "-E", "UTF8",
            "--locale=C"
        ]

        pw_file = data_dir.parent / "pw_temp.txt"
        if password:
            data_dir.parent.mkdir(parents=True, exist_ok=True)
            pw_file.write_text(f"{password}\n", encoding="utf-8")
            cmd.extend(["--pwfile", str(pw_file)])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"initdb failed:\n{res.stderr}")
                sys.exit(1)
            print("Cluster initialized successfully.")
        finally:
            if pw_file.exists():
                pw_file.unlink()
    else:
        print(f"PostgreSQL cluster data directory verified at {data_dir}")


def start_server():
    """Verifies existing connection or starts PostgreSQL server if local."""
    target_url = get_target_db_url()
    url_obj = make_url(target_url)
    target_db_name = url_obj.database or "smart_postal_db"
    admin_url = str(url_obj.set(database="postgres"))
    target_port = str(url_obj.port or 5432)

    # 1. Quick probe: is PostgreSQL already accepting connections on target database?
    try:
        engine = create_engine(target_url)
        with engine.connect() as conn:
            ver = conn.execute(text("SELECT version();")).scalar()
            print("PostgreSQL server is already active and accepting connections:")
            print(f"  Version: {ver}")
            print(f"  Target Database: {target_db_name}")
            return
    except Exception:
        pass

    # 2. Server not responding; detect local installation binaries
    pg_bin_dir = detect_postgres_bin()
    data_dir = get_postgres_data_dir()
    log_file = data_dir.parent / "postgres.log"

    print(f"Detected PostgreSQL binaries at: {pg_bin_dir}")
    init_cluster(pg_bin_dir, data_dir, target_url)

    pg_ctl_exe = pg_bin_dir / ("pg_ctl.exe" if sys.platform == "win32" else "pg_ctl")

    # Check status
    status_cmd = [str(pg_ctl_exe), "-D", str(data_dir), "status"]
    res = subprocess.run(status_cmd, capture_output=True, text=True)
    if "is running" in res.stdout:
        print("PostgreSQL server process is running.")
    else:
        start_cmd = [
            str(pg_ctl_exe),
            "-D", str(data_dir),
            "-l", str(log_file),
            "-o", f"-p {target_port}",
            "start"
        ]
        res = subprocess.run(start_cmd, capture_output=True, text=True)
        print(f"pg_ctl start: {res.stdout.strip()}")
        time.sleep(2)

    # Ensure target database exists
    for attempt in range(5):
        try:
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                db_exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": target_db_name}
                ).scalar()
                if not db_exists:
                    conn.execute(text(f'CREATE DATABASE "{target_db_name}";'))
                    print(f"Created database '{target_db_name}'.")
                else:
                    print(f"Database '{target_db_name}' verified.")
            break
        except Exception as e:
            print(f"Waiting for PostgreSQL to accept admin connections ({attempt+1}/5)... ({e})")
            time.sleep(2)

    # Final target connection verification
    target_engine = create_engine(target_url)
    with target_engine.connect() as conn:
        ver = conn.execute(text("SELECT version();")).scalar()
        print("\nPostgreSQL Connection Verified Successfully:")
        print(f"  Version: {ver}")
        print(f"  Target Database: {target_db_name}")


def stop_server():
    """Stops the local PostgreSQL server."""
    pg_bin_dir = detect_postgres_bin()
    data_dir = get_postgres_data_dir()
    pg_ctl_exe = pg_bin_dir / ("pg_ctl.exe" if sys.platform == "win32" else "pg_ctl")
    stop_cmd = [str(pg_ctl_exe), "-D", str(data_dir), "stop", "-m", "fast"]
    res = subprocess.run(stop_cmd, capture_output=True, text=True)
    print(res.stdout)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop_server()
    else:
        start_server()
