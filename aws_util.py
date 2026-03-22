import os
from dataclasses import dataclass

import boto3


@dataclass
class S3Uploader:
    bucket: str
    default_acl: str = "public-read"

    def __post_init__(self):
        self.s3 = boto3.resource("s3")
        self.client = boto3.client("s3")

    def upload_file(self, key_prefix: str, filename: str, acl: str | None = None) -> str:
        with open(filename, "rb") as f:
            object_name = os.path.basename(filename)
            key = os.path.join(key_prefix, object_name)
            self.s3.Bucket(self.bucket).put_object(
                Key=key,
                Body=f.read(),
                ACL=acl or self.default_acl,
            )
        return key

    def health_check(self) -> bool:
        content = self.client.list_objects_v2(Bucket=self.bucket, MaxKeys=10)
        return len(content.get("Contents", [])) > 0
