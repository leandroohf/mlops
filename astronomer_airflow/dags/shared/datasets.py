import os
from airflow.datasets import Dataset
#from dotenv import load_dotenv

#load_dotenv(dotenv_path="astronomer_airflow/.env")

# NOTE: Define a dataset (e.g., a table or file)
# this is just a string indentifier
MY_DATA = Dataset(os.getenv('TRAINING_DATASET'))

# NOTE: other options
#MY_DATA = Dataset("bigquery://my-project.my_dataset.my_table")
#MY_DATA = Dataset("postgresql://my-db/my_schema.my_table")
