from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/rzeszow.db"
    DATA_DIR: str = "./data"
    DATA_SOURCE: str = "json_cache"  # or "otodom"
    OTODOM_BASE_URL: str = "https://www.otodom.pl"
    REQUEST_DELAY_S: float = 2.0
    USER_AGENT: str = "RzeszowYieldAnalyser/1.0 (private research; contact: owner)"

    RENO_COST_READY: float = 0.0
    RENO_COST_FINISHING: float = 1800.0
    RENO_COST_RENOVATION: float = 2800.0

    VACANCY_RATE: float = 0.08
    ANNUAL_COSTS_RATE: float = 0.20

    SCORE_WEIGHT_DISCOUNT: float = 0.5
    SCORE_WEIGHT_YIELD: float = 0.4
    SCORE_WEIGHT_PRICE: float = 0.1

    INCLUDED_CONDITIONS: List[str] = ["ready", "finishing", "renovation"]

    SCHEDULE_INTERVAL_HOURS: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
