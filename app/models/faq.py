from app.database import get_database
from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime
import numpy as np
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class FAQ:
    """
    FAQ Model with Vector Search support (Synchronous)
    
    Fields:
    - question: str (the FAQ question)
    - answer: str (the FAQ answer)
    - embedding: List[float] (vector embedding from nomic-embed-text)
    - created_at: datetime
    """

    collection_name = "faqs"

    @classmethod
    def get_collection(cls):
        """Get MongoDB collection"""
        db = get_database()
        return db[cls.collection_name]

    @classmethod
    async def insert(cls, question: str, answer: str, embedding: List[float]) -> Any:
        """
        Insert new FAQ with embedding
        """
        try:
            collection = cls.get_collection()
            
            document = {
                "question": question,
                "answer": answer,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            }
            
            result = collection.insert_one(document)
            return result
        except Exception as e:
            logger.error(f"Error inserting FAQ: {str(e)}")
            raise

    @classmethod
    async def find_all(cls) -> List[Dict[str, Any]]:
        """
        Get all FAQs (without embeddings for frontend)
        Falls back to JSON file if MongoDB is unavailable
        """
        try:
            collection = cls.get_collection()
            
            faqs = []
            cursor = collection.find({}, {"embedding": 0})
            for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                faqs.append(doc)
            
            # If we got data, return it
            if faqs:
                return faqs
                
            # If collection is empty, try loading from JSON
            logger.info("FAQ collection empty, loading from JSON fallback...")
            json_file = Path(__file__).parent.parent / "data" / "faq_data.json"
            if json_file.exists():
                with open(json_file, 'r') as f:
                    json_data = json.load(f)
                    # Add _id field for consistency
                    for idx, faq in enumerate(json_data):
                        faq["_id"] = f"faq_{idx:02d}"
                    return json_data
            
            return []
        except Exception as e:
            logger.error(f"Error fetching FAQs from DB: {str(e)}, trying JSON fallback...")
            # Fallback to JSON if database fails
            try:
                json_file = Path(__file__).parent.parent / "data" / "faq_data.json"
                if json_file.exists():
                    with open(json_file, 'r') as f:
                        json_data = json.load(f)
                        for idx, faq in enumerate(json_data):
                            faq["_id"] = f"faq_{idx:02d}"
                        return json_data
            except Exception as json_err:
                logger.error(f"JSON fallback also failed: {str(json_err)}")
            
            return []

    @classmethod
    async def vector_search(
        cls,
        embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search using vector similarity (cosine distance)
        
        Note: For production, use MongoDB Atlas Vector Search
        This is a simple implementation using manual similarity
        """
        try:
            collection = cls.get_collection()
            
            # Get all FAQs with embeddings
            faqs_with_scores = []
            cursor = collection.find({}, {"embedding": 1, "question": 1, "answer": 1})
            for doc in cursor:
                if "embedding" in doc and doc["embedding"]:
                    try:
                        # Calculate cosine similarity
                        score = cls._cosine_similarity(
                            embedding,
                            doc["embedding"]
                        )
                        
                        faqs_with_scores.append({
                            "_id": str(doc["_id"]),
                            "question": doc.get("question", ""),
                            "answer": doc.get("answer", ""),
                            "similarity_score": score
                        })
                    except Exception as e:
                        logger.warning(f"Error calculating similarity: {str(e)}")
                        continue
            
            # Sort by similarity (descending) and return top K
            faqs_with_scores.sort(
                key=lambda x: x["similarity_score"],
                reverse=True
            )
            
            # Remove similarity_score before returning
            result = []
            for faq in faqs_with_scores[:limit]:
                faq_copy = faq.copy()
                del faq_copy["similarity_score"]
                result.append(faq_copy)
            
            return result

        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return []

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        """
        try:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            
            dot_product = np.dot(vec1_np, vec2_np)
            magnitude = np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np)
            
            if magnitude == 0:
                return 0.0
            
            return float(dot_product / magnitude)
        except Exception as e:
            logger.error(f"Similarity calculation error: {str(e)}")
            return 0.0

    @classmethod
    async def delete_by_id(cls, faq_id: str):
        """
        Delete FAQ by ID
        """
        try:
            collection = cls.get_collection()
            
            result = collection.delete_one({
                "_id": ObjectId(faq_id)
            })
            
            return result
        except Exception as e:
            logger.error(f"Error deleting FAQ: {str(e)}")
            raise

    @classmethod
    async def create_indexes(cls):
        """
        Create indexes for FAQ collection
        """
        try:
            collection = cls.get_collection()
            
            # Text index for keyword search (optional)
            collection.create_index([("question", "text"), ("answer", "text")])
            logger.info("Text index created for FAQs")
            
        except Exception as e:
            logger.warning(f"Index creation warning: {str(e)}")

