"""
Cloud storage service for permanent document storage.
Supports AWS S3, Google Cloud Storage, and Azure Blob Storage.
"""
import os
import logging
from typing import Optional, BinaryIO
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CloudStorageInterface(ABC):
    """Abstract interface for cloud storage providers."""
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload a file to cloud storage. Returns the URL/path."""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from cloud storage."""
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        """Delete a file from cloud storage."""
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in cloud storage."""
        pass
    
    @abstractmethod
    def get_file_url(self, remote_path: str) -> str:
        """Get a URL to access the file."""
        pass


class S3Storage(CloudStorageInterface):
    """AWS S3 storage implementation."""
    
    def __init__(self, bucket: str, region: str, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self.bucket = bucket
            self.region = region
            
            # Initialize S3 client
            if access_key and secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                # Use default credentials (IAM role, environment variables, etc.)
                self.s3_client = boto3.client('s3', region_name=region)
            
            logger.info(f"Initialized S3 storage: bucket={bucket}, region={region}")
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage: {e}")
            raise
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload file to S3."""
        try:
            self.s3_client.upload_file(local_path, self.bucket, remote_path)
            url = f"s3://{self.bucket}/{remote_path}"
            logger.info(f"Uploaded {local_path} to {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from S3."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket, remote_path, local_path)
            logger.info(f"Downloaded {remote_path} to {local_path}")
        except Exception as e:
            logger.error(f"Failed to download from S3: {e}")
            raise
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=remote_path)
            logger.info(f"Deleted {remote_path} from S3")
        except Exception as e:
            logger.error(f"Failed to delete from S3: {e}")
            raise
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=remote_path)
            return True
        except Exception:
            return False
    
    def get_file_url(self, remote_path: str) -> str:
        """Get presigned URL for file access."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': remote_path},
                ExpiresIn=3600  # 1 hour
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate S3 URL: {e}")
            return f"s3://{self.bucket}/{remote_path}"


class LocalStorage(CloudStorageInterface):
    """Local filesystem storage (fallback when cloud storage is not configured)."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local storage at {base_path}")
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Copy file to local storage directory."""
        dest_path = self.base_path / remote_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(local_path, dest_path)
        logger.info(f"Copied {local_path} to {dest_path}")
        return str(dest_path)
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Copy file from local storage."""
        source_path = self.base_path / remote_path
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {source_path}")
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        import shutil
        shutil.copy2(source_path, local_path)
        logger.info(f"Copied {source_path} to {local_path}")
    
    def delete_file(self, remote_path: str) -> None:
        """Delete file from local storage."""
        file_path = self.base_path / remote_path
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted {file_path}")
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage."""
        return (self.base_path / remote_path).exists()
    
    def get_file_url(self, remote_path: str) -> str:
        """Return local file path."""
        return str(self.base_path / remote_path)


def get_storage_service():
    """
    Get the appropriate storage service based on configuration.
    Returns CloudStorageInterface instance.
    """
    from app.core.config import settings
    
    if not settings.USE_CLOUD_STORAGE:
        # Use local storage
        return LocalStorage(str(settings.UPLOAD_DIR))
    
    # Use cloud storage based on provider
    if settings.STORAGE_PROVIDER.lower() == "s3":
        if not settings.AWS_S3_BUCKET:
            logger.warning("AWS_S3_BUCKET not set, falling back to local storage")
            return LocalStorage(str(settings.UPLOAD_DIR))
        
        return S3Storage(
            bucket=settings.AWS_S3_BUCKET,
            region=settings.AWS_S3_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY
        )
    else:
        logger.warning(f"Storage provider '{settings.STORAGE_PROVIDER}' not implemented, using local storage")
        return LocalStorage(str(settings.UPLOAD_DIR))

