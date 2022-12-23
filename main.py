from dotenv import load_dotenv
import uvicorn
import os
import pathlib
from fastapi import FastAPI
from app.routers import reservoir
from app.internal.settings import Settings
from app.utils.log import Log

BASEDIR = pathlib.Path().resolve()
os.environ["APP_INSTALLDIR"] = os.path.dirname(os.path.abspath(__file__))
load_dotenv(
    pathlib.Path(os.getenv("APP_INSTALLDIR")).joinpath(".env"),
    override=True,
)
Settings.read_environments()

app = FastAPI(root_path=Settings.root_path)

app.include_router(reservoir.router)

if __name__ == "__main__":
    Log.configure_logging(BASEDIR)
    uvicorn.run(
        "main:app", host=Settings.host, port=Settings.port, log_level="info"
    )
