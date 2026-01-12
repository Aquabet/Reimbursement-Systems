import os
import boto3
from abc import ABC, abstractmethod


class StorageReader(ABC):
    @abstractmethod
    def read_file(self, storage_path):
        pass


class LocalStorageReader(StorageReader):
    def read_file(self, storage_path):
        with open(storage_path, 'rb') as f:
            return f.read()


class S3StorageReader(StorageReader):
    def __init__(self):
        self.s3 = boto3.client('s3')

    def read_file(self, storage_path):
        # Parse s3://bucket/key format
        if not storage_path.startswith('s3://'):
            raise ValueError(f"Invalid S3 path: {storage_path}")

        parts = storage_path[5:].split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''

        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()


class StorageReaderFactory:
    @staticmethod
    def create_reader(storage_path, aws_region=None):
        if storage_path.startswith('s3://'):
            if aws_region:
                boto3.setup_default_session(region_name=aws_region)
            return S3StorageReader()
        else:
            return LocalStorageReader()
