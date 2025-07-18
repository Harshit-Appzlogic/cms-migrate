"""
MongoDB database setup and configuration for CMS Migration System
"""
import os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections and collections for the CMS migration system"""
    
    def __init__(self, uri: Optional[str] = None, database_name: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            uri: MongoDB URI (defaults to environment variable)
            database_name: Database name (defaults to environment variable)
        """
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", "cms_migration")
        
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        
    def connect(self) -> bool:
        """
        Connect to MongoDB
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {self.uri}")
            
            # Create collections and indexes
            self._setup_collections()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def _setup_collections(self):
        """Create collections and indexes"""
        if self.db is None:
            return
            
        # Create collections
        collections = [
            "component_schemas",
            "extracted_data", 
            "component_types",
            "page_types"
        ]
        
        for collection_name in collections:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        if self.db is None:
            return
            
        # Component schemas indexes
        self.db.component_schemas.create_index("uid", unique=True)
        self.db.component_schemas.create_index("title")
        
        # Extracted data indexes
        self.db.extracted_data.create_index("component_type")
        self.db.extracted_data.create_index("source_file")
        self.db.extracted_data.create_index("confidence")
        
        # Component types indexes
        self.db.component_types.create_index("type", unique=True)
        
        # Page types indexes
        self.db.page_types.create_index("page_name", unique=True)
        self.db.page_types.create_index("detected_components")
        
        logger.info("Database indexes created successfully")
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get a collection by name
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection: MongoDB collection
        """
        if self.db is None:
            raise RuntimeError("Database not connected")
        
        return self.db[collection_name]
    
    def save_component_schema(self, schema: Dict[str, Any]) -> str:
        """
        Save a component schema to database
        
        Args:
            schema: Component schema dictionary
            
        Returns:
            str: Inserted document ID
        """
        collection = self.get_collection("component_schemas")
        result = collection.insert_one(schema)
        logger.info(f"Saved component schema: {schema.get('title', 'Unknown')}")
        return str(result.inserted_id)
    
    def save_extracted_data(self, data: Dict[str, Any]) -> str:
        """
        Save extracted data to database
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            str: Inserted document ID
        """
        collection = self.get_collection("extracted_data")
        result = collection.insert_one(data)
        logger.info(f"Saved extracted data from: {data.get('source_file', 'Unknown')}")
        return str(result.inserted_id)
    
    def save_component_type(self, component_type: Dict[str, Any]) -> str:
        """
        Save component type metadata
        
        Args:
            component_type: Component type dictionary
            
        Returns:
            str: Inserted document ID
        """
        collection = self.get_collection("component_types")
        result = collection.replace_one(
            {"type": component_type["type"]},
            component_type,
            upsert=True
        )
        logger.info(f"Saved component type: {component_type['type']}")
        return str(result.upserted_id or result.modified_count)
    
    def save_page_type(self, page_data: Dict[str, Any]) -> str:
        """
        Save page type information
        
        Args:
            page_data: Page type dictionary
            
        Returns:
            str: Inserted document ID
        """
        collection = self.get_collection("page_types")
        result = collection.replace_one(
            {"page_name": page_data["page_name"]},
            page_data,
            upsert=True
        )
        logger.info(f"Saved page type: {page_data['page_name']}")
        return str(result.upserted_id or result.modified_count)
    
    def get_component_schemas(self) -> List[Dict[str, Any]]:
        """Get all component schemas"""
        collection = self.get_collection("component_schemas")
        return list(collection.find({}))
    
    def get_extracted_data(self, component_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get extracted data, optionally filtered by component type
        
        Args:
            component_type: Filter by component type
            
        Returns:
            List of extracted data documents
        """
        collection = self.get_collection("extracted_data")
        query = {"component_type": component_type} if component_type else {}
        return list(collection.find(query))
    
    def get_component_types(self) -> List[Dict[str, Any]]:
        """Get all component types"""
        collection = self.get_collection("component_types")
        return list(collection.find({}))
    
    def get_page_types(self) -> List[Dict[str, Any]]:
        """Get all page types"""
        collection = self.get_collection("page_types")
        return list(collection.find({}))
    
    def clear_collection(self, collection_name: str) -> int:
        """
        Clear all documents from a collection
        
        Args:
            collection_name: Name of collection to clear
            
        Returns:
            int: Number of documents deleted
        """
        collection = self.get_collection(collection_name)
        result = collection.delete_many({})
        logger.info(f"Cleared {result.deleted_count} documents from {collection_name}")
        return result.deleted_count
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")


# Global database instance
db_manager = DatabaseManager()