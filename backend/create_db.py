import os
import psycopg2

def create_database():
    """
    Creates the PostgreSQL database if it doesn't exist
    """
    # Database connection parameters
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', 'root')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'resume_shortlister')
    
    print(f"Connecting to PostgreSQL (host: {db_host}, user: {db_user})...")
    
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="postgres"  # Connect to default postgres database
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        exists = cursor.fetchone()
        
        # Create database if it doesn't exist
        if not exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"✅ Database '{db_name}' created successfully")
        else:
            print(f"✅ Database '{db_name}' already exists")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("✅ Database setup complete")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    if create_database():
        print("\nDatabase is ready! You can now run the application:")
        print("  python run.py")
    else:
        print("\nFailed to set up the database. Please check your PostgreSQL installation and credentials.") 