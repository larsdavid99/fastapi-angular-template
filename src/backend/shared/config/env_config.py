from pathlib import Path

from dotenv import load_dotenv

# .env sits in src/backend, two levels up
load_dotenv(Path(__file__).parents[2] / ".env")
