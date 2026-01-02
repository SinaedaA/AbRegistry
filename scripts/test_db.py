# import models, call init_db() and insert pseudo-data to test database connection and table creation
from models.database import RawSequence, IngestionLog, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import json

def test_db():
    # Initialize the database
    init_db()
    
    # Create a new session
    engine = create_engine("postgresql+psycopg2://airflow:airflow@postgres/airflow")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create pseudo-data
    raw_sequence = RawSequence(
        source="TestSource",
        ab_name="TestAntibody",
        ab_format="IgG1",
        ch1_isotype=json.dumps({"heavy_chain": "IgG1"}),
        vd_lc=json.dumps({"light_chain": "kappa"}),
        heavy_chain1="ATGC" * 35,
        light_chain1="ATGC" * 28,
        target=json.dumps(["Target1", "Target2"]),
        notes="This is a test antibody.",
        genetics=json.dumps({"type": "humanized"}),
        development_metadata=json.dumps({"phase": "Phase 1"}),
        structural_metadata=json.dumps({"structure": "predicted"})
    )
    
    ingestion_log = IngestionLog(
        run_id="test_run_001",
        source="TestSource",
        count=1,
        status="SUCCESS",
        timestamp=datetime.utcnow()
    )
    
    # Add and commit pseudo-data to the session
    session.add(raw_sequence)
    session.add(ingestion_log)
    session.commit()
    
    print("Test data inserted successfully.")
    
    # Close the session
    session.close()

if __name__ == "__main__":
    test_db()