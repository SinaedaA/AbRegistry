from database.database import engine, Base
from database.models import RawSequence, IngestionLog
from sqlalchemy.schema import CreateSchema

def init_db():
    conn = engine.connect()
    schemas = ['staging', 'intermediate', 'mart']
    for schema in schemas:
         if not conn.dialect.has_schema(conn, schema):
             print(f"Creating '{schema}' schema...")
             conn.execute(CreateSchema(schema))
         else:
             print(f"'{schema}' schema already exists.")
    conn.commit()
    conn.close()

def create_tables():
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Tables created successfully.")
