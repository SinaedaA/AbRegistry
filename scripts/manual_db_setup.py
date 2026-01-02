## DON'T USE. This is replaced by dags/setup_database.py, using airflow to orchestrate the steps.
# runs init_db, create_tables and load_data
from init_db import main as init_db
from create_tables import main as create_tables
from load_data import main as load_data

def setup_database():
    print("Initializing database schemas...")
    init_db()

    create_tables()
    
    print("Loading initial data...")
    load_data()
    
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()