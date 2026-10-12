#!/usr/bin/env python3
"""
Database initialization script for ChromaDB with sample user data.
Run this script to initialize the database with sample users.

For local development only. It creates users with well-known passwords,
so never run it on a production server.
"""

from conn import db

def main():
    print("Initializing ChromaDB database...")
    
    # Initialize sample data
    db.initialize_sample_data()
    
    print("\nDatabase initialization completed!")
    print("Sample users created:")
    print("- admin@admin.com (password: admin)")
    print("- user1@example.com (password: password123)")
    print("- user2@example.com (password: password456)")
    
    # Display all users
    print("\nAll users in database:")
    users = db.get_all_users()
    for user in users:
        print(f"- {user['email']} ({user['username']}) - {user['full_name']}")

if __name__ == "__main__":
    main() 