from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.leads import router as leads_router
from app.api.v1.pipelines import router as pipelines_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(pipelines_router)




