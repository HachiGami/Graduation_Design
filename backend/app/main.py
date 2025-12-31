from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import (
    connect_to_mongo, 
    close_mongo_connection,
    connect_to_neo4j,
    close_neo4j_connection
)
from .routers import resources, personnel, dependencies, activities, demo_data, resource_usage

app = FastAPI(title="乳业生产建模系统API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resources.router)
app.include_router(personnel.router)
app.include_router(dependencies.router)
app.include_router(activities.router)
app.include_router(resource_usage.router)
app.include_router(demo_data.router)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await connect_to_neo4j()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    await close_neo4j_connection()

@app.get("/")
async def root():
    return {"message": "乳业生产建模系统API"}
