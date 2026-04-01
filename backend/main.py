from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    patient_router,
    agreement_router,
    enrollment_router,
    medication_router,
    monodrug_router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Alleanza Tracking", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(patient_router)
    app.include_router(agreement_router)
    app.include_router(enrollment_router)
    app.include_router(medication_router)
    app.include_router(monodrug_router)

    @app.get("/")
    async def root():
        return {"message": "API de Alleanza Tracking funcionando"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=9999, reload=True)
