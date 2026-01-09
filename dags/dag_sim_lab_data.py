from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import json
from datetime import datetime

def task_simulate_lab_data():
    """
    Task to simulate lab data by generating mutated antibody sequences
    and adding lab metadata.
    """
    from scripts.generate_lab_data import generate_lab_sequences
    import random
    import traceback
    try:
        potential_names = json.load(open('data/raw/potential_names.json'))
        num_sequences = random.randint(1, 5)
        chosen_names = random.sample(potential_names, num_sequences)

        # rewrite the potential_names file without the chosen names
        with open('data/raw/potential_names.json', 'w') as f:
            json.dump([name for name in potential_names if name not in chosen_names], f)
        
        generate_lab_sequences(
            num_sequences=num_sequences,
            outfile=f"data/lab_uploads/lab_data_{datetime.now().strftime('%Y%m%d_%H%m%S')}.csv",
            ab_names=chosen_names
        )
        # defined here, instead of inside 'op_kwargs' in DAG ==> only evaluated at runtime
        print("Lab data simulation completed successfully.")
    except Exception as e:
        print("Error during lab data simulation:")
        traceback.print_exc()
        raise

with DAG(
    dag_id = 'simulate_lab_data',
    start_date = datetime(2024, 1, 1),
    # schedule every 6 hours
    schedule = '0 */6 * * *', # dev only
    #schedule = ('@daily'),
    catchup = False,
    description = '[DEV ONLY] Generate simulated lab antibody sequence data with mutations and metadata'
) as dag:
    
    simulate_lab_data_task = PythonOperator(
        task_id='simulate_lab_data',
        python_callable=task_simulate_lab_data
    )

    simulate_lab_data_task