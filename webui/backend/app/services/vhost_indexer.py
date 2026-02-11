"""
Vhost indexer service using SQLite for fast querying of large vhost datasets (6k+ vhosts)
"""
import os
import sqlite3
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class VhostIndexer:
    """SQLite-backed indexer for virtual hosts with background refresh"""

    DB_PATH = "/opt/fauxnet/config/vhosts_index.db"
    REFRESH_INTERVAL_HOURS = 2

    # Import paths from VhostsManager to avoid circular imports
    VHOSTS_WWW_DIR = "/opt/fauxnet/vhosts_www"
    VHOSTS_CONFIG_DIR = "/opt/fauxnet/vhosts_config"
    CONFIG_DIR = "/opt/fauxnet/config"
    SCRAPE_SITES_FILE = f"{CONFIG_DIR}/scrape_sites.txt"
    CUSTOM_SITES_FILE = f"{CONFIG_DIR}/custom_sites.txt"

    _background_task = None
    _is_running = False

    @classmethod
    @contextmanager
    def _get_db_connection(cls):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(cls.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @classmethod
    def _init_database(cls):
        """Initialize the SQLite database schema"""
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)

        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vhosts (
                    name TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    config_path TEXT NOT NULL,
                    type TEXT NOT NULL,
                    has_cert INTEGER NOT NULL,
                    has_nginx_config INTEGER NOT NULL,
                    cert_path TEXT,
                    nginx_config_path TEXT,
                    size_bytes INTEGER,
                    file_count INTEGER,
                    modified TEXT,
                    last_indexed TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON vhosts(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_indexed ON vhosts(last_indexed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_cert ON vhosts(has_cert)")

            # Metadata table for tracking last full refresh
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()
            logger.info("Vhost indexer database initialized")

    @classmethod
    async def _get_vhost_size_fast(cls, vhost_www_path: str) -> tuple:
        """Fast calculation of directory size and file count using du command"""
        try:
            # Use du for fast size calculation (in bytes)
            proc = await asyncio.create_subprocess_exec(
                'du', '-sb', vhost_www_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            size_bytes = int(stdout.decode().split()[0]) if proc.returncode == 0 else 0

            # Use find for fast file count
            proc = await asyncio.create_subprocess_exec(
                'find', vhost_www_path, '-type', 'f',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            file_count = len(stdout.decode().strip().split('\n')) if stdout else 0

            return (size_bytes, file_count)
        except Exception:
            return (0, 0)

    @classmethod
    async def _load_site_lists(cls) -> tuple:
        """Load scraped, custom, and fauxnet site lists"""
        scraped_sites = set()
        if os.path.exists(cls.SCRAPE_SITES_FILE):
            try:
                with open(cls.SCRAPE_SITES_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            from urllib.parse import urlparse
                            parsed = urlparse(line if '://' in line else f'http://{line}')
                            hostname = parsed.netloc or parsed.path
                            if hostname:
                                scraped_sites.add(hostname)
            except Exception:
                pass

        custom_sites = set()
        if os.path.exists(cls.CUSTOM_SITES_FILE):
            try:
                with open(cls.CUSTOM_SITES_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            from urllib.parse import urlparse
                            parsed = urlparse(line if '://' in line else f'http://{line}')
                            hostname = parsed.netloc or parsed.path
                            if hostname:
                                custom_sites.add(hostname)
            except Exception:
                pass

        fauxnet_sites = {'fauxnet.info', 'www.msftncsi.com'}

        return scraped_sites, custom_sites, fauxnet_sites

    @classmethod
    async def _index_single_vhost(
        cls,
        vhost_name: str,
        scraped_sites: set,
        custom_sites: set,
        fauxnet_sites: set,
        include_stats: bool = True
    ) -> Dict:
        """Index a single vhost and return its data"""
        vhost_www_path = os.path.join(cls.VHOSTS_WWW_DIR, vhost_name)
        vhost_config_path = os.path.join(cls.VHOSTS_CONFIG_DIR, vhost_name)
        cert_path = os.path.join(vhost_config_path, f"{vhost_name}.cer")
        nginx_config_path = os.path.join(vhost_config_path, "nginx.conf")

        # Determine vhost type
        if vhost_name in custom_sites:
            vhost_type = "custom"
        elif vhost_name in fauxnet_sites:
            vhost_type = "fauxnet"
        elif vhost_name in scraped_sites:
            vhost_type = "scraped"
        else:
            vhost_type = "discovered"

        # Calculate size/file_count if requested
        if include_stats:
            total_size, file_count = await cls._get_vhost_size_fast(vhost_www_path)
        else:
            total_size, file_count = None, None

        # Get modification time from www directory
        try:
            mtime = os.path.getmtime(vhost_www_path)
            modified_date = datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            modified_date = None

        return {
            "name": vhost_name,
            "path": vhost_www_path,
            "config_path": vhost_config_path,
            "type": vhost_type,
            "has_cert": os.path.exists(cert_path),
            "has_nginx_config": os.path.exists(nginx_config_path),
            "cert_path": cert_path if os.path.exists(cert_path) else None,
            "nginx_config_path": nginx_config_path if os.path.exists(nginx_config_path) else None,
            "size_bytes": total_size,
            "file_count": file_count,
            "modified": modified_date,
        }

    @classmethod
    async def update_vhost(cls, vhost_name: str, include_stats: bool = True):
        """
        Update a single vhost in the index

        Call this when a user edits/adds a vhost to refresh only that entry
        """
        logger.info(f"Updating index for vhost: {vhost_name}")

        # Check if vhost exists
        vhost_www_path = os.path.join(cls.VHOSTS_WWW_DIR, vhost_name)
        if not os.path.exists(vhost_www_path) or not os.path.isdir(vhost_www_path):
            # Vhost doesn't exist, remove from index if present
            with cls._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vhosts WHERE name = ?", (vhost_name,))
                conn.commit()
            logger.info(f"Removed {vhost_name} from index (no longer exists)")
            return

        # Load site lists
        scraped_sites, custom_sites, fauxnet_sites = await cls._load_site_lists()

        # Index the vhost
        vhost_data = await cls._index_single_vhost(
            vhost_name, scraped_sites, custom_sites, fauxnet_sites, include_stats
        )

        # Upsert into database
        now = datetime.now().isoformat()
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vhosts (
                    name, path, config_path, type, has_cert, has_nginx_config,
                    cert_path, nginx_config_path, size_bytes, file_count, modified,
                    last_indexed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    path = excluded.path,
                    config_path = excluded.config_path,
                    type = excluded.type,
                    has_cert = excluded.has_cert,
                    has_nginx_config = excluded.has_nginx_config,
                    cert_path = excluded.cert_path,
                    nginx_config_path = excluded.nginx_config_path,
                    size_bytes = excluded.size_bytes,
                    file_count = excluded.file_count,
                    modified = excluded.modified,
                    last_indexed = excluded.last_indexed,
                    updated_at = excluded.updated_at
            """, (
                vhost_data["name"],
                vhost_data["path"],
                vhost_data["config_path"],
                vhost_data["type"],
                1 if vhost_data["has_cert"] else 0,
                1 if vhost_data["has_nginx_config"] else 0,
                vhost_data["cert_path"],
                vhost_data["nginx_config_path"],
                vhost_data["size_bytes"],
                vhost_data["file_count"],
                vhost_data["modified"],
                now,  # last_indexed
                now,  # created_at
                now   # updated_at
            ))
            conn.commit()

        logger.info(f"Updated index for vhost: {vhost_name}")

    @classmethod
    async def rebuild_index(cls, include_stats: bool = True, progress_callback=None):
        """
        Rebuild the entire vhost index from filesystem

        Args:
            include_stats: Whether to calculate size/file count (slower but complete)
            progress_callback: Optional callback function(current, total) for progress tracking
        """
        logger.info("Starting full vhost index rebuild...")
        start_time = datetime.now()

        if not os.path.exists(cls.VHOSTS_WWW_DIR):
            logger.warning(f"Vhosts directory does not exist: {cls.VHOSTS_WWW_DIR}")
            return

        # Load site lists
        scraped_sites, custom_sites, fauxnet_sites = await cls._load_site_lists()

        # Get list of vhost directories
        vhost_names = [
            name for name in os.listdir(cls.VHOSTS_WWW_DIR)
            if os.path.isdir(os.path.join(cls.VHOSTS_WWW_DIR, name))
        ]

        total_vhosts = len(vhost_names)
        logger.info(f"Found {total_vhosts} vhosts to index")

        # Process vhosts in batches for better performance
        batch_size = 50
        indexed_count = 0

        for i in range(0, len(vhost_names), batch_size):
            batch = vhost_names[i:i + batch_size]

            # Process batch in parallel
            tasks = [
                cls._index_single_vhost(
                    vhost_name,
                    scraped_sites,
                    custom_sites,
                    fauxnet_sites,
                    include_stats
                )
                for vhost_name in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Insert batch into database
            now = datetime.now().isoformat()
            with cls._get_db_connection() as conn:
                cursor = conn.cursor()
                for result in batch_results:
                    if isinstance(result, dict):
                        cursor.execute("""
                            INSERT OR REPLACE INTO vhosts (
                                name, path, config_path, type, has_cert, has_nginx_config,
                                cert_path, nginx_config_path, size_bytes, file_count, modified,
                                last_indexed, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            result["name"],
                            result["path"],
                            result["config_path"],
                            result["type"],
                            1 if result["has_cert"] else 0,
                            1 if result["has_nginx_config"] else 0,
                            result["cert_path"],
                            result["nginx_config_path"],
                            result["size_bytes"],
                            result["file_count"],
                            result["modified"],
                            now,  # last_indexed
                            now,  # created_at
                            now   # updated_at
                        ))
                        indexed_count += 1
                    elif isinstance(result, Exception):
                        logger.warning(f"Error indexing vhost: {result}")

                conn.commit()

            # Progress callback
            if progress_callback:
                progress_callback(indexed_count, total_vhosts)

            # Log progress every batch
            if (i + batch_size) % 500 == 0:
                logger.info(f"Indexed {indexed_count}/{total_vhosts} vhosts...")

        # Update metadata
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES ('last_full_refresh', ?)
            """, (datetime.now().isoformat(),))
            conn.commit()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Index rebuild complete: {indexed_count} vhosts indexed in {elapsed:.2f}s")

    @classmethod
    def get_vhosts(cls, include_stats: bool = False) -> List[Dict]:
        """
        Get all vhosts from the index

        Args:
            include_stats: If True, include size_bytes and file_count.
                          If False, these fields will be None for faster queries.

        Returns:
            List of vhost dictionaries
        """
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()

            if include_stats:
                cursor.execute("""
                    SELECT name, path, config_path, type, has_cert, has_nginx_config,
                           cert_path, nginx_config_path, size_bytes, file_count, modified
                    FROM vhosts
                    ORDER BY name
                """)
            else:
                cursor.execute("""
                    SELECT name, path, config_path, type, has_cert, has_nginx_config,
                           cert_path, nginx_config_path, NULL as size_bytes,
                           NULL as file_count, modified
                    FROM vhosts
                    ORDER BY name
                """)

            rows = cursor.fetchall()

            vhosts = []
            for row in rows:
                vhosts.append({
                    "name": row["name"],
                    "path": row["path"],
                    "config_path": row["config_path"],
                    "type": row["type"],
                    "has_cert": bool(row["has_cert"]),
                    "has_nginx_config": bool(row["has_nginx_config"]),
                    "cert_path": row["cert_path"],
                    "nginx_config_path": row["nginx_config_path"],
                    "size_bytes": row["size_bytes"],
                    "file_count": row["file_count"],
                    "modified": row["modified"],
                })

            return vhosts

    @classmethod
    def get_vhost(cls, vhost_name: str) -> Optional[Dict]:
        """Get a single vhost from the index"""
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, path, config_path, type, has_cert, has_nginx_config,
                       cert_path, nginx_config_path, size_bytes, file_count, modified
                FROM vhosts
                WHERE name = ?
            """, (vhost_name,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "name": row["name"],
                "path": row["path"],
                "config_path": row["config_path"],
                "type": row["type"],
                "has_cert": bool(row["has_cert"]),
                "has_nginx_config": bool(row["has_nginx_config"]),
                "cert_path": row["cert_path"],
                "nginx_config_path": row["nginx_config_path"],
                "size_bytes": row["size_bytes"],
                "file_count": row["file_count"],
                "modified": row["modified"],
            }

    @classmethod
    def delete_vhost(cls, vhost_name: str):
        """Remove a vhost from the index"""
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vhosts WHERE name = ?", (vhost_name,))
            conn.commit()
        logger.info(f"Removed {vhost_name} from index")

    @classmethod
    def get_statistics(cls) -> Dict:
        """Get statistics from the index (very fast)"""
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()

            # Get counts
            cursor.execute("SELECT COUNT(*) as total FROM vhosts")
            total_vhosts = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM vhosts WHERE has_cert = 1")
            vhosts_with_certs = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM vhosts WHERE has_nginx_config = 1")
            vhosts_with_nginx = cursor.fetchone()["total"]

            # Get sums
            cursor.execute("""
                SELECT
                    COALESCE(SUM(size_bytes), 0) as total_size,
                    COALESCE(SUM(file_count), 0) as total_files
                FROM vhosts
                WHERE size_bytes IS NOT NULL
            """)
            row = cursor.fetchone()

            return {
                "total_vhosts": total_vhosts,
                "total_size_bytes": row["total_size"],
                "total_files": row["total_files"],
                "vhosts_with_certs": vhosts_with_certs,
                "vhosts_with_nginx_config": vhosts_with_nginx,
            }

    @classmethod
    def get_last_refresh_time(cls) -> Optional[datetime]:
        """Get the timestamp of the last full refresh"""
        with cls._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'last_full_refresh'")
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row["value"])
            return None

    @classmethod
    async def _background_refresh_loop(cls):
        """Background task that refreshes the index every 2 hours"""
        logger.info(f"Starting background refresh loop (every {cls.REFRESH_INTERVAL_HOURS} hours)")

        while cls._is_running:
            try:
                # Wait for the interval
                await asyncio.sleep(cls.REFRESH_INTERVAL_HOURS * 3600)

                if not cls._is_running:
                    break

                logger.info("Background refresh triggered")
                await cls.rebuild_index(include_stats=True)

            except asyncio.CancelledError:
                logger.info("Background refresh loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background refresh loop: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait a minute before retrying

    @classmethod
    async def start_background_refresh(cls, initial_rebuild: bool = False):
        """
        Start the background refresh task

        Args:
            initial_rebuild: If True, perform an initial full rebuild before starting the loop
        """
        if cls._is_running:
            logger.warning("Background refresh already running")
            return

        # Initialize database
        cls._init_database()

        # Check if index exists and is recent
        last_refresh = cls.get_last_refresh_time()
        needs_rebuild = True

        if last_refresh:
            age = datetime.now() - last_refresh
            if age < timedelta(hours=cls.REFRESH_INTERVAL_HOURS):
                needs_rebuild = False
                logger.info(f"Index is fresh (last refresh: {age.total_seconds() / 60:.1f} minutes ago)")

        # Perform initial rebuild if needed or requested
        if initial_rebuild or needs_rebuild:
            logger.info("Performing initial index rebuild...")
            await cls.rebuild_index(include_stats=True)

        # Start background loop
        cls._is_running = True
        cls._background_task = asyncio.create_task(cls._background_refresh_loop())
        logger.info("Background refresh task started")

    @classmethod
    async def stop_background_refresh(cls):
        """Stop the background refresh task"""
        if not cls._is_running:
            return

        logger.info("Stopping background refresh task...")
        cls._is_running = False

        if cls._background_task:
            cls._background_task.cancel()
            try:
                await cls._background_task
            except asyncio.CancelledError:
                pass
            cls._background_task = None

        logger.info("Background refresh task stopped")
