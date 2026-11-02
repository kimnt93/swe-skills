use super::Loader;

/// S3-compatible object store (RustFS, MinIO, AWS): S3_ENDPOINT, S3_REGION, S3_BUCKET,
/// S3_FORCE_PATH_STYLE, S3_ACCESS_KEY[_FILE], S3_SECRET_KEY[_FILE] (see s3.env.example in the
/// rust-infra skill).
#[derive(Clone)]
pub struct S3 {
    pub endpoint: String,
    pub region: String,
    pub bucket: String,
    pub force_path_style: bool,
    pub access_key: String,
    pub secret_key: String,
}

impl S3 {
    pub fn load(l: &mut Loader) -> S3 {
        S3 {
            endpoint: l.req("S3_ENDPOINT"),
            region: l.str("S3_REGION", "us-east-1"),
            bucket: l.req("S3_BUCKET"),
            force_path_style: l.flag("S3_FORCE_PATH_STYLE", true),
            access_key: l.secret("S3_ACCESS_KEY"),
            secret_key: l.secret("S3_SECRET_KEY"),
        }
    }
}
