"""Read-only verification script for PregAI database schema updates."""
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import models, crud, database
from sqlalchemy import inspect

EXPECTED_TABLES = ['users', 'images', 'predictions', 'conversations', 'system_logs']

def verify_tables():
    print("Checking database tables...")
    inspector = inspect(database.engine)
    tables = inspector.get_table_names()
    missing_tables = []
    
    for table in EXPECTED_TABLES:
        if table in tables:
            print(f"  [OK] Table '{table}' exists.")
        else:
            print(f"  [MISSING] Table '{table}' does NOT exist.")
            missing_tables.append(table)

    return missing_tables

def verify_models():
    print("\nVerifying models and CRUD functions...")
    missing_tables = verify_tables()
    if missing_tables:
        print("  [ERROR] Missing required tables. Run migrations before verifying data access.")
        return False
    
    db = next(database.get_db())
    try:
        model_tables = set(models.Base.metadata.tables)
        missing_model_tables = [table for table in EXPECTED_TABLES if table not in model_tables]
        if missing_model_tables:
            print(f"  [ERROR] Models do not define expected tables: {', '.join(missing_model_tables)}")
            return False
        print("  [OK] Model metadata contains expected tables.")
        
        # Verify CRUD reads without mutating production data.
        test_user = crud.get_user_by_email(db, "test@example.com")
        if test_user:
            print(f"  [INFO] Test user already exists: {test_user.user_id}")
        else:
            print("  [OK] User lookup completed.")

        return True
    except Exception as e:
        print(f"  [ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = verify_models()
    raise SystemExit(0 if success else 1)
