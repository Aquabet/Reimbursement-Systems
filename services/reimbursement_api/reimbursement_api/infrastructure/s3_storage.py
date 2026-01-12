import boto3
from werkzeug.utils import secure_filename

from .storage import Storage


class S3Storage(Storage):
    def __init__(self, bucket_name):
        self.s3 = boto3.client("s3")
        self.bucket_name = bucket_name

    def save(self, file, filename):
        filename = secure_filename(filename)
        self.s3.upload_fileobj(file, self.bucket_name, filename)
        return f"s3://{self.bucket_name}/{filename}"

    def retrieve(self, filename):
        # Generate a presigned URL to access the file
        return self.s3.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket_name, "Key": filename}, ExpiresIn=3600
        )
