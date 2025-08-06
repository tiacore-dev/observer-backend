import os

from dotenv import load_dotenv
from tiacore_lib.config import ConfigName

from app import create_app
from metrics.logger import setup_logger

load_dotenv()


PORT = 8000

CONFIG_NAME = ConfigName(os.getenv("CONFIG_NAME", "development"))

setup_logger()


app = create_app(config_name=CONFIG_NAME)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(PORT), reload=True)
