# runs init_db, create_tables and load_data
import init_db, create_tables, load_data

def setup_database():
    print("Initializing database schemas...")
    init_db.main()
    
    print("Creating database tables...")
    create_tables.main()
    
    print("Loading initial data...")
    load_data.main()
    
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()