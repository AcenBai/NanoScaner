from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import features, ml, preprocess, report, signal

app = FastAPI(title="Nanopore Current Signal AI Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "message": "service is healthy"}


app.include_router(signal.router, prefix="/api/signal", tags=["signal"])
app.include_router(preprocess.router, prefix="/api/preprocess", tags=["preprocess"])
app.include_router(features.router, prefix="/api/features", tags=["features"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(report.router, prefix="/api/report", tags=["report"])
