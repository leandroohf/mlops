# handlers.py
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any, Dict, Optional, Union, Literal
from google.cloud import storage

import os
import io
from loguru import logger
import pandas as pd
import pickle   
import joblib

SUPPORTED_FORMATS = Literal["json","txt" ,"parquet", "csv", "pickle"]
BUCKET_NAME = os.getenv("BUCKET_NAME", "bike-artifacts")

class LocalArtifactHandler():

    def __init__(self):
        pass

    def _infer_fmt_from_name(self,name: str) -> SUPPORTED_FORMATS:
    
        ext = Path(name).suffix.lower()
        if ext == ".parquet":
            return "parquet"
        if ext == ".csv":
            return "csv"
        if ext in (".pkl", ".pickle", ".joblib"):
            return "pickle"
        raise ValueError(f"Unsupported extension '{ext}'. Use .parquet, .csv, .pkl/.pickle/.joblib.")
        
    def _ensure_folder_exist(self,path):

        Path(path).mkdir(parents=True, exist_ok=True)
    
    def _ensure_parent_dir(self, file_path) -> None:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
    def save(self, obj, cached_file_path: str) -> None:

        file_type = self._infer_fmt_from_name(cached_file_path)

        self._ensure_parent_dir(cached_file_path)

        if file_type == 'csv':

            assert type(obj) == pd.DataFrame
            obj.to_csv(cached_file_path,index=False)

        elif file_type == 'json':

            assert type(obj) in [dict, list], "obj must be a dict or list"
            with open(cached_file_path, 'w') as f:
                json.dump(obj, f, ensure_ascii=False)

        elif file_type == 'parquet':

            assert type(obj) == pd.DataFrame
            obj.to_parquet(cached_file_path, 
                           engine="pyarrow",
                           compression="snappy",
                           index=False)
            
        elif file_type == 'txt':

            assert type(obj) == str, "obj must be a string"
            with open(cached_file_path, 'w', encoding='utf-8') as file:
                file.write(obj)

        else:

            joblib.dump(obj, cached_file_path)

    def load(self, fname: str) -> None:

        file_type = self._infer_fmt_from_name(fname)

        if file_type == 'csv':

            return pd.read_csv(fname)

        elif file_type == 'txt':
            with open(fname, 'r', encoding='utf-8') as file:
                return file.read()

        elif file_type == 'json':
            with open(fname, 'r', encoding='utf-8') as file:
                return json.load(file)
        
        elif file_type == 'parquet':

            return pd.read_parquet(fname, engine="pyarrow")

        else:
            try:
                return joblib.load(fname)
            
            except Exception as e:
                raise ValueError(f"Error loading file with joblib: {fname}. Error: {e}")

    def copy(self, source_path: str, dest_path: str) -> None:

        logger.debug(f"Copying {source_path} to {dest_path}")

        try: 

            # Get the parent directory of dest_path and create it if it doesn't exist
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

class GCSArtifactHandler(LocalArtifactHandler):

    def __init__(self,
        bucket_name: str = BUCKET_NAME,
        root_path: str = 'dev'):

        assert bucket_name.startswith("gs://"), f"Invalid GCS bucket name: {bucket_name}"

        self._bucket_name = bucket_name
        self._root_path = root_path

        try:
            self.storage_client = storage.Client()

        except Exception as e:
            logger.error(f"Error while creating GCP storage client.")
            logger.error(e)
            raise e

    def get_number_blob_in_env(self) -> bool:
        """
        Checks if the given environment already exists in the bucket.
        """
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(self._bucket_name)
            
            # Create the full path for the environment
            env = str(Path(self._root_path))
            
            # Check for blobs with the given prefix
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
        """Uploads a file to the bucket."""

        try:
            #self.storage_client = storage.Client()
            bucket = self.storage_client.bucket(self._bucket_name)

            bucket_blob_path = Path(self._root_path) / destination_blob_name

            blob = bucket.blob(str(bucket_blob_path))

            blob.upload_from_filename(source_file_name)
            logger.debug(f"File {source_file_name} uploaded to {bucket_blob_path}")

        except Exception as e:

            logger.error("Somethings is wrong")
            logger.error(e)
            raise (e)

    def download(self, blob_name: str, destination_file_path: str):
        """Uploads a file to the bucket."""

        try:
            #self.storage_client = storage.Client()
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

    def save(self, obj, cached_file_path: str) -> None:

        super()._ensure_folder_exist('.cache')
        destination_file_name = Path('.cache') / Path(cached_file_path).name
        super().save(obj, destination_file_name)

        logger.debug(f"uploading object: {cached_file_path} -> {destination_file_name}")
        self.upload(str(destination_file_name), str(cached_file_path))

    def load(self, fname: str) -> None:

        super()._ensure_folder_exist('.cache')
        destination_file_name = Path('.cache') / Path(fname).name

        self.download(fname, destination_file_name)
        
        return super().load(destination_file_name)

    def check_exists(self, blob_name: str) -> bool:

        # NOTE: Ex: blob_name = 'preprocessed/lookback_data.pkl'
        try:
            # Construct the full path
            full_path = f"{self._root_path}/{blob_name}"

            bucket = self.storage_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)

            return blob.exists()
        
        except Exception as e:
            print(f"Error checking if blob exists: {e}")
            return False 
