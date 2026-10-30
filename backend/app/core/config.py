import os
import re
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.engine import URL

# Load variables from .env file (checks backend/.env or cwd)
backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)
else:
    load_dotenv()


class Settings(BaseModel):
    # App
    APP_NAME: str = Field(default_factory=lambda: os.getenv("APP_NAME", "SalesBattlecard API"))
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "True").lower() in ("true", "1", "yes"))
    AUTH_USERNAME: str = Field(default_factory=lambda: os.getenv("AUTH_USERNAME", ""))
    AUTH_PASSWORD: str = Field(default_factory=lambda: os.getenv("AUTH_PASSWORD", ""))
    INTERACTION_SOURCES: str = Field(default_factory=lambda: os.getenv("INTERACTION_SOURCES", "whats_app,ticket_email,pm1call_log,pm1cti_event,customer_thread,rep_thread"))
    ENABLE_TEST_ANALYZE: bool = Field(default_factory=lambda: os.getenv("ENABLE_TEST_ANALYZE", "false").lower() == "true")
    MAX_EVIDENCE_BYTES: int = Field(default_factory=lambda: int(os.getenv("MAX_EVIDENCE_BYTES", "240000")), ge=12000, le=1000000)
    ALLOWED_ORIGINS: str = Field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000"))

    # MySQL Database
    DB_HOST: str = Field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    DB_PORT: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    DB_USER: str = Field(default_factory=lambda: os.getenv("DB_USER", "root"))
    DB_PASSWORD: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    DB_NAME: str = Field(default_factory=lambda: os.getenv("DB_NAME", "paramantra_salesbattle"))

    # Configurable Table Names
    TABLE_LEADS: str = Field(default_factory=lambda: os.getenv("TABLE_LEADS", "leads"))
    TABLE_INTERACTIONS: str = Field(default_factory=lambda: os.getenv("TABLE_INTERACTIONS", "lead_interactions"))

    # Configurable Columns - Leads
    COL_LEAD_ID: str = Field(default_factory=lambda: os.getenv("COL_LEAD_ID", "id"))
    COL_LEAD_NAME: str = Field(default_factory=lambda: os.getenv("COL_LEAD_NAME", "name"))
    COL_LEAD_COMPANY: str = Field(default_factory=lambda: os.getenv("COL_LEAD_COMPANY", "company"))
    COL_LEAD_STATUS: str = Field(default_factory=lambda: os.getenv("COL_LEAD_STATUS", "status"))
    COL_LEAD_STAGE: str = Field(default_factory=lambda: os.getenv("COL_LEAD_STAGE", "stage"))
    COL_LEAD_ASSIGNED_TO: str = Field(default_factory=lambda: os.getenv("COL_LEAD_ASSIGNED_TO", "assigned_to"))

    # Configurable Columns - Interactions
    COL_INT_ID: str = Field(default_factory=lambda: os.getenv("COL_INT_ID", "id"))
    COL_INT_LEAD_ID: str = Field(default_factory=lambda: os.getenv("COL_INT_LEAD_ID", "lead_id"))
    COL_INT_CONTENT: str = Field(default_factory=lambda: os.getenv("COL_INT_CONTENT", "notes"))
    COL_INT_TYPE: str = Field(default_factory=lambda: os.getenv("COL_INT_TYPE", "interaction_type"))
    COL_INT_DIRECTION: str = Field(default_factory=lambda: os.getenv("COL_INT_DIRECTION", "direction"))
    COL_INT_CREATED_AT: str = Field(default_factory=lambda: os.getenv("COL_INT_CREATED_AT", "created_at"))

    # OpenAI
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    OPENAI_SUMMARY_MODEL: str = Field(default_factory=lambda: os.getenv("OPENAI_SUMMARY_MODEL", ""))

    @property
    def database_url(self) -> URL:
        """Constructs the SQLAlchemy connection URL for MySQL."""
        return URL.create("mysql+pymysql", username=self.DB_USER, password=self.DB_PASSWORD,
                          host=self.DB_HOST, port=self.DB_PORT, database=self.DB_NAME,
                          query={"charset": "utf8mb4"})

    @model_validator(mode="after")
    def validate_configuration(self):
        for key, value in self.model_dump().items():
            if key.startswith(("TABLE_", "COL_")) and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
                raise ValueError(f"{key} must be a SQL identifier")
        sources = self.INTERACTION_SOURCES.split(",")
        allowed = {"whats_app", "ticket_email", "pm1call_log", "pm1cti_event", "customer_thread", "rep_thread", "generic"}
        if not sources or any(s.strip() not in allowed for s in sources):
            raise ValueError("INTERACTION_SOURCES contains an unsupported source")
        if bool(self.AUTH_USERNAME) != bool(self.AUTH_PASSWORD):
            raise ValueError("Set both AUTH_USERNAME and AUTH_PASSWORD")
        if self.APP_ENV != "development" and (not self.AUTH_USERNAME or len(self.AUTH_PASSWORD) < 16):
            raise ValueError("Hosted mode requires AUTH_USERNAME and AUTH_PASSWORD (at least 16 characters)")
        if "*" in self.cors_origins:
            raise ValueError("ALLOWED_ORIGINS must contain explicit origins")
        return self

    @property
    def cors_origins(self) -> List[str]:
        """Returns parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()

