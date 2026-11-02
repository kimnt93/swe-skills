//! S3-compatible object store adapter (RustFS, MinIO, AWS S3) on the AWS SDK for Rust: static
//! credentials from the environment, a custom endpoint, path-style addressing. Nothing else in the
//! service imports the SDK.

use aws_sdk_s3::{
    config::{
        BehaviorVersion, Credentials, Region, RequestChecksumCalculation,
        ResponseChecksumValidation,
    },
    primitives::ByteStream,
    Client,
};
use svc_core::{config::S3 as Settings, Error, Result};

#[derive(Clone)]
pub struct ObjectStore {
    client: Client,
    bucket: String,
}

/// Messages from the SDK can include endpoints and request ids: keep them out of API-visible
/// errors.
fn storage(_e: impl std::fmt::Debug) -> Error {
    Error::Storage("object store operation failed".into())
}

impl ObjectStore {
    pub fn open(s: &Settings) -> ObjectStore {
        let creds = Credentials::new(&s.access_key, &s.secret_key, None, None, "env");
        let conf = aws_sdk_s3::Config::builder()
            .behavior_version(BehaviorVersion::latest())
            .region(Region::new(s.region.clone()))
            .endpoint_url(&s.endpoint)
            .credentials_provider(creds)
            .force_path_style(s.force_path_style) // http://host:9000/<bucket>/<key>
            // S3-compatible stores do not all accept the SDK's default trailing checksums: send
            // them only when required.
            .request_checksum_calculation(RequestChecksumCalculation::WhenRequired)
            .response_checksum_validation(ResponseChecksumValidation::WhenRequired)
            .build();
        ObjectStore {
            client: Client::from_conf(conf),
            bucket: s.bucket.clone(),
        }
    }

    /// The bucket exists and the credentials may use it.
    pub async fn ping(&self) -> Result<()> {
        self.client
            .head_bucket()
            .bucket(&self.bucket)
            .send()
            .await
            .map(|_| ())
            .map_err(storage)
    }

    /// Creates the bucket when missing (tests and local setup; provision buckets in deployments).
    pub async fn ensure_bucket(&self) -> Result<()> {
        if self.ping().await.is_ok() {
            return Ok(());
        }
        self.client
            .create_bucket()
            .bucket(&self.bucket)
            .send()
            .await
            .map(|_| ())
            .map_err(storage)
    }

    pub async fn put(&self, key: &str, body: Vec<u8>, content_type: &str) -> Result<()> {
        self.client
            .put_object()
            .bucket(&self.bucket)
            .key(key)
            .content_type(content_type)
            .body(ByteStream::from(body))
            .send()
            .await
            .map(|_| ())
            .map_err(storage)
    }

    /// Reads the whole object (use `get_stream` for large ones); a missing key is
    /// `Error::NotFound`.
    pub async fn get(&self, key: &str) -> Result<Vec<u8>> {
        let out = self
            .client
            .get_object()
            .bucket(&self.bucket)
            .key(key)
            .send()
            .await
            .map_err(|e| {
                if e.as_service_error().is_some_and(|s| s.is_no_such_key()) {
                    Error::NotFound
                } else {
                    storage(e)
                }
            })?;
        Ok(out
            .body
            .collect()
            .await
            .map_err(storage)?
            .into_bytes()
            .to_vec())
    }

    pub async fn delete(&self, key: &str) -> Result<()> {
        self.client
            .delete_object()
            .bucket(&self.bucket)
            .key(key)
            .send()
            .await
            .map(|_| ())
            .map_err(storage)
    }

    /// At most `limit` keys under `prefix` (bounded; page with the continuation token for more).
    pub async fn list(&self, prefix: &str, limit: i32) -> Result<Vec<String>> {
        let out = self
            .client
            .list_objects_v2()
            .bucket(&self.bucket)
            .prefix(prefix)
            .max_keys(limit)
            .send()
            .await
            .map_err(storage)?;
        Ok(out
            .contents()
            .iter()
            .filter_map(|o| o.key().map(str::to_string))
            .collect())
    }
}
