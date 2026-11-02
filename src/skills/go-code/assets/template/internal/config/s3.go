package config

// S3 is the S3-compatible object store (RustFS, MinIO, AWS). Loaded from S3_ENDPOINT, S3_REGION,
// S3_BUCKET, S3_FORCE_PATH_STYLE, S3_ACCESS_KEY[_FILE], S3_SECRET_KEY[_FILE] (see s3.env.example in
// the go-s3 skill).
type S3 struct {
	Endpoint, Region, Bucket, AccessKey, SecretKey string
	ForcePathStyle                                 bool
}

// LoadS3 reads the S3_* variables.
func LoadS3(l *Loader) S3 {
	return S3{
		Endpoint:       l.Req("S3_ENDPOINT"),
		Region:         l.Str("S3_REGION", "us-east-1"),
		Bucket:         l.Req("S3_BUCKET"),
		ForcePathStyle: l.Bool("S3_FORCE_PATH_STYLE", true),
		AccessKey:      l.Secret("S3_ACCESS_KEY"),
		SecretKey:      l.Secret("S3_SECRET_KEY"),
	}
}
