from database.database import engine, Base
from sqlalchemy.schema import CreateSchema

def main():
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

if __name__ == "__main__":
    main()