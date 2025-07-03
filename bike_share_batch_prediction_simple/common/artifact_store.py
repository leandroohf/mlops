import json
import pandavro as pdx
from pathlib import Path
from urllib.parse import  quote
import joblib
from google.cloud import storage
import pandas as pd
import yaml

from loguru import logger
import os
import sys
import shutil

# NOTE: export LOG_LEVEL=DEBUG  <== for debug messages  (default is INFO)
log_level = os.getenv("LOG_LEVEL", "INFO")

# Set up the logger
logger.remove()  # Remove any previously added sinks
logger.add(sys.stdout, level=log_level)

def load_config(path="common/config.yaml"):
    return yaml.safe_load(open(path))

CONFIG = load_config()

class LocalArtifactStore():

    SUPPORTED_EXTENSIONS = ['.csv', '.json', '.avro', '.txt', '.pkl']

    def __init__(self):
        pass

    def save(self, obj, cached_file_path: str, avro_schema: dict = None) -> None:

        ext = Path(cached_file_path).suffix.lower()
        assert ext in self.SUPPORTED_EXTENSIONS,\
                f"Unsupported file extension: {Path(cached_file_path).suffix}"
        Path(cached_file_path).parent.mkdir(parents=True, exist_ok=True)

        if ext == '.csv':
            assert type(obj) == pd.DataFrame
            obj.to_csv(cached_file_path,index=False)

        elif ext == '.json':
            with open(cached_file_path, 'w') as f:
                json.dump(obj, f, ensure_ascii=False)

        elif ext == ".avro":
            assert type(obj) == pd.DataFrame, "obj must be a pandas DataFrame"
            assert avro_schema is not None, "avro_schema must be provided"
            # NOTE: pandavaros expect path string and not Path object (PosixPath(...))
            # NOTE: snnapy is fast compression algo developed by google
            pdx.to_avro(str(cached_file_path), obj, schema=avro_schema, codec="snappy")

        elif ext == '.txt':
            assert type(obj) == str, "obj must be a string"
            with open(cached_file_path, 'w', encoding='utf-8') as file:
                file.write(obj)

        elif ext == '.pkl':
            joblib.dump(obj, cached_file_path)

    def load(self, fname: str) -> None:

        ext = Path(fname).suffix.lower()

        if ext == '.csv':
            return pd.read_csv(fname)

        elif ext  == '.txt':
            with open(fname, 'r', encoding='utf-8') as file:
                return file.read()

        elif ext == '.json':
            with open(fname, 'r', encoding='utf-8') as file:
                return json.load(file)
        
        else:
            try:
                return joblib.load(fname)
            
            except Exception as e:
                raise ValueError(f"Error loading file with joblib: {fname}. Error: {e}")

    def copy(self, source_path: str, dest_path: str) -> None:

        logger.debug(f"Copying {source_path} to {dest_path}")

        try: 

            # NOTE: Get the parent directory of dest_path and create it if it doesn't exist
            dest_folder = Path(dest_path).parent
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            shutil.copy(source_path, dest_path)

        except Exception as e:

            logger.error(f"Somethings is wrong. Failed to copy: {source_path} to {dest_path}")
            logger.error(e)
            raise (e)

    def check_exists(self, path: str) -> bool:

        # NOTE: Ex: path = 'preprocessed/lookback_data.pkl'

        return Path(path).exists()

class GCPArtifactStore(LocalArtifactStore):

    def __init__(self,
        root_path: str = 'dev',
        bucket_name: str = None
        ):

        self._bucket_name = CONFIG["bucket_name"]if bucket_name is None else bucket_name
        self._root_path = root_path

        self._local_cache_dir = Path('.cache')
        self._local_cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.storage_client = storage.Client()

        except Exception as e:
            logger.error(f"Error while creating GCP storage client.")
            logger.error(e)
            raise e

    def get_number_blob_in_env(self) -> bool:
        """
        Count number of blobs in the bucket
        """
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(self._bucket_name)
            
            env = str(Path(self._root_path))
            
            # NOTE: Check for blobs with the given prefix
            blobs = list(bucket.list_blobs(prefix=env))
            count = sum(1 for _ in blobs)

            logger.warning(f"env: {env}; _root_path: {self._root_path}")
            logger.warning(f"Found {count} blobs with prefix {env}")
  
            return count

        except Exception as e:
            logger.error(f"Error while checking the existence of environment {env}.")
            logger.error(e)
            raise e

    def upload(self, source_file_name: str, destination_blob_name: str):

        try:
            bucket = self.storage_client.bucket(self._bucket_name)
            bucket_blob_path = Path(self._root_path) / destination_blob_name

            blob = bucket.blob(str(bucket_blob_path))
            blob.upload_from_filename(source_file_name)
            logger.debug(f"File {source_file_name} uploaded to {bucket_blob_path}")

        except Exception as e:

            logger.error(f"{self._bucket_name}: Failed to upload {source_file_name} to {bucket_blob_path}")
            logger.error(e)
            raise (e)

    def download(self, blob_name: str, destination_file_path: str):

        try:
    
            bucket = self.storage_client.bucket(self._bucket_name)

            blob_path = quote(self._root_path + r"/" + blob_name)

            blob = bucket.blob(str(blob_path))

            blob.download_to_filename(destination_file_path)

            logger.debug(
                f"Blob {blob_name} downloaded to {destination_file_path}"
            )

        except Exception as e:

            logger.error(f"Somethings is wrong: Failed to download {blob_name} to {destination_file_path}")
            logger.error(e)
            raise (e)

    def save(self, obj, cached_file_path: str, avro_schema: dict = None) -> None:

        destination_file_name = Path(self._local_cache_dir) / Path(cached_file_path).name
        super().save(obj, destination_file_name, avro_schema)
  
        logger.debug(f"uploading object: {cached_file_path} -> {destination_file_name}")
        self.upload(str(destination_file_name), str(cached_file_path))

    def load(self, fname: str) -> None:

        destination_file_name = Path(self._local_cache_dir) / Path(fname).name
        self.download(fname, destination_file_name)
        
        return super().load(destination_file_name)

    def check_exists(self, blob_name: str) -> bool:

        # NOTE: Ex: blob_name = 'preprocessed/lookback_data.pkl'
        try:

            full_path = f"{self._root_path}/{blob_name}"

            bucket = self.storage_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)

            return blob.exists()
        
        except Exception as e:
            print(f"Error checking if blob exists: {e}")
            return False 

class MLflowArtifactStore(LocalArtifactStore):

    def __init__(self):
        logger.warning("MLflowArtifactStore is not implemented yet.")
        pass