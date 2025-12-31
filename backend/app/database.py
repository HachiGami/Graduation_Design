from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import AsyncGraphDatabase
from .config import settings

# MongoDB globals
client = None
database = None

# Neo4j globals
neo4j_driver = None

async def connect_to_mongo():
    global client, database
    client = AsyncIOMotorClient(settings.mongodb_url)
    database = client[settings.database_name]

async def close_mongo_connection():
    global client
    if client:
        client.close()

def get_database():
    return database

async def connect_to_neo4j():
    global neo4j_driver
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        # Verify connection
        await neo4j_driver.verify_connectivity()
        print("Connected to Neo4j")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        raise e

async def close_neo4j_connection():
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        print("Closed Neo4j connection")

def get_neo4j_driver():
    return neo4j_driver
