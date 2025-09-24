"""
Minimal Superset configuration
"""
# Basic configuration
SECRET_KEY = "your-secret-key-here"
JWT_SECRET_KEY = "your-jwt-secret-key-here-make-it-long-enough-32-bytes"

# SQLite database (simple, no setup required)
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# Disable async queries to avoid JWT issues
GLOBAL_ASYNC_QUERIES = False

# Basic feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
}

# Disable CORS for now
ENABLE_CORS = False
ENABLE_PROXY_FIX = False

# Simple cache
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
}

# Row limits
ROW_LIMIT = 50000
VIZ_ROW_LIMIT = 10000

# Timeout settings
SUPERSET_WEBSERVER_TIMEOUT = 60
SUPERSET_WEBSERVER_PROTOCOL = "http"

# Custom database engines for Trino
ADDITIONAL_DATABASE_ENGINES = {
    "trino": {
        "name": "Trino",
        "driver": "trino",
        "supports_catalog": True,
        "supports_schema": True,
        "supports_cross_schema": True,
        "supports_views": True,
        "supports_joins": True,
        "supports_subqueries": True,
        "supports_cte": True,
        "supports_window_functions": True,
        "supports_aggregate_functions": True,
        "supports_union": True,
        "supports_intersect": True,
        "supports_except": True,
        "supports_limit": True,
        "supports_offset": True,
        "supports_order_by": True,
        "supports_group_by": True,
        "supports_having": True,
        "supports_distinct": True,
        "supports_arrays": True,
        "supports_json": True,
        "supports_unicode": True,
        "supports_quoted_identifiers": True,
        "supports_quoted_table_names": True,
        "supports_quoted_column_names": True,
        "supports_quoted_schema_names": True,
        "supports_quoted_catalog_names": True,
    }
}

# Custom SQL Lab settings
SQLLAB_CTAS_NO_LIMIT = True
SQLLAB_TIMEOUT = 300
SQLLAB_DEFAULT_DBID = None
