import chromadb
from chromadb.config import Settings
import bcrypt
import os
import uuid

class DatabaseManager:
    def __init__(self):
        # Initialize ChromaDB with persistent storage
        self.persist_directory = "./chroma_db"
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Get or create the users collection
        try:
            self.users_collection = self.client.get_collection("users")
        except:
            self.users_collection = self.client.create_collection("users")
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_user(self, username, email, password, full_name=None):
        """Create a new user in the database"""
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email)
            if existing_user:
                return False, "User already exists"
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user document
            user_id = str(uuid.uuid4())
            user_data = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "full_name": full_name or username,
                "created_at": str(uuid.uuid1().time)
            }
            
            # Add to ChromaDB collection
            self.users_collection.add(
                documents=[f"User: {username} Email: {email}"],
                metadatas=[user_data],
                ids=[user_id]
            )
            
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            results = self.users_collection.query(
                query_texts=[f"Email: {email}"],
                n_results=1,
                where={"email": email}
            )
            
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                return results['metadatas'][0][0]
            return None
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if user and self.verify_password(password, user['password']):
            return user
        return None
    
    def get_all_users(self):
        """Get all users from the database"""
        try:
            results = self.users_collection.get()
            return results['metadatas'] if results['metadatas'] else []
        except Exception as e:
            print(f"Error getting all users: {str(e)}")
            return []
    
    def initialize_sample_data(self):
        """Initialize sample user data"""
        sample_users = [
            {
                "username": "admin",
                "email": "admin@admin.com",
                "password": "admin",
                "full_name": "System Administrator"
            },
            {
                "username": "user1",
                "email": "user1@example.com", 
                "password": "password123",
                "full_name": "John Doe"
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "password456", 
                "full_name": "Jane Smith"
            }
        ]
        
        for user in sample_users:
            success, message = self.create_user(
                user['username'],
                user['email'],
                user['password'],
                user['full_name']
            )
            print(f"Creating user {user['email']}: {message}")

# Global database instance
db = DatabaseManager()
