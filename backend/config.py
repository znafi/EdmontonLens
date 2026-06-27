"""Centralised application configuration loaded from environment variables.

All settings are read via ``pydantic-settings`` so the application never
hardcodes credentials. The local dev environment works without any GCP
credentials by falling back to a local PostgreSQL/SQLite database.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Google Cloud ---
    google_application_credentials: str | None = None
    gcp_project_id: str | None = None
    bigquery_dataset: str = "edmonton_lens"

    # --- Gemini ---
    gemini_api_key: str | None = None
    # Model name for the CityBot agent. We make just two Gemini calls per
    # question (generate SQL, summarise rows), so gemini-2.5-flash's thinking
    # latency is fine and it answers in a few seconds. (gemini-1.5-pro was
    # retired in 2025, and this key has no quota for gemini-2.0-flash.)
    gemini_model: str = "gemini-2.5-flash"

    # --- Local DB (dev) ---
    # Defaults to a local SQLite file so the app runs with zero external deps.
    database_url: str = "sqlite:///./data/edmonton_lens.db"

    # --- MySQL (local dev / Data Administration NL role) ---
    mysql_database_url: str = "mysql+pymysql://edmonton:password@localhost:3306/edmonton_lens"

    # --- SQL Server (local dev / Data Administration NL role) ---
    sqlserver_database_url: str = (
        "mssql+pyodbc://sa:EdmontonLens123!@localhost:1433/edmonton_lens"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    )

    # --- Edmonton Open Data ---
    edmonton_open_data_app_token: str | None = None

    # --- Frontend ---
    next_public_api_base_url: str = "http://localhost:8000"

    # --- Data source URLs ---
    socrata_base_url: str = "https://data.edmonton.ca/resource/"
    gtfs_feed_url: str = "https://data.edmonton.ca/api/geospatial/gtfs"
    arcgis_base_url: str = "https://maps.edmonton.ca/arcgis/rest/services/"

    @property
    def mysql_enabled(self) -> bool:
        """True when a non-default MySQL URL is set, or always True so dev loads work."""
        return bool(self.mysql_database_url)

    @property
    def sqlserver_enabled(self) -> bool:
        """True when the SQL Server URL is configured."""
        return bool(self.sqlserver_database_url)

    @property
    def bigquery_enabled(self) -> bool:
        """True when enough config is present to talk to BigQuery."""
        return bool(self.gcp_project_id and self.google_application_credentials)

    @property
    def gemini_enabled(self) -> bool:
        """True when a Gemini API key is configured."""
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton ``Settings`` instance."""
    return Settings()


settings = get_settings()
