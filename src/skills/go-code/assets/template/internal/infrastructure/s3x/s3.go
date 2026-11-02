// Package s3x wraps the AWS SDK for Go v2 for any S3-compatible store (RustFS, MinIO, AWS S3):
// static credentials from the environment, a custom endpoint, path-style addressing. Nothing else
// in the service imports the SDK.
package s3x

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/aws/smithy-go"

	"example.com/service/internal/config"
)

// ErrNotFound reports a missing object.
var ErrNotFound = errors.New("object not found")

// Client is a bucket-scoped S3 client for any S3-compatible store.
type Client struct {
	s3     *s3.Client
	bucket string
}

// Open builds the client from configuration (static credentials, custom endpoint, path-style
// addressing).
func Open(c config.S3) *Client {
	cfg := aws.Config{
		Region:      c.Region,
		Credentials: credentials.NewStaticCredentialsProvider(c.AccessKey, c.SecretKey, ""),
		// S3-compatible stores do not all accept the SDK's default trailing checksums: send them
		// only when required.
		RequestChecksumCalculation: aws.RequestChecksumCalculationWhenRequired,
		ResponseChecksumValidation: aws.ResponseChecksumValidationWhenRequired,
	}
	client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.BaseEndpoint = aws.String(c.Endpoint)

		// Path style is http://host:9000/<bucket>/<key>; virtual-hosted style needs wildcard DNS.
		o.UsePathStyle = c.ForcePathStyle
	})

	return &Client{s3: client, bucket: c.Bucket}
}

// Ping checks that the bucket exists and the credentials may use it.
func (c *Client) Ping(ctx context.Context) error {
	_, err := c.s3.HeadBucket(ctx, &s3.HeadBucketInput{Bucket: &c.bucket})
	return err
}

// EnsureBucket creates the bucket if it is missing (tests and local setup; provision buckets in
// deployments).
func (c *Client) EnsureBucket(ctx context.Context) error {
	if err := c.Ping(ctx); err == nil {
		return nil
	}
	_, err := c.s3.CreateBucket(ctx, &s3.CreateBucketInput{Bucket: &c.bucket})
	var owned *types.BucketAlreadyOwnedByYou
	if errors.As(err, &owned) {
		return nil
	}
	return err
}

// Put stores body under key.
func (c *Client) Put(ctx context.Context, key string, body []byte, contentType string) error {
	_, err := c.s3.PutObject(ctx, &s3.PutObjectInput{
		Bucket:      &c.bucket,
		Key:         &key,
		Body:        bytes.NewReader(body),
		ContentType: &contentType,
	})

	return err
}

// Get reads the whole object; use GetStream for large objects.
func (c *Client) Get(ctx context.Context, key string) ([]byte, error) {
	rc, err := c.GetStream(ctx, key)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = rc.Close()
	}()

	return io.ReadAll(rc)
}

// GetStream opens the object for streaming; the caller closes it.
func (c *Client) GetStream(ctx context.Context, key string) (io.ReadCloser, error) {
	out, err := c.s3.GetObject(ctx, &s3.GetObjectInput{Bucket: &c.bucket, Key: &key})
	if err != nil {
		var nsk *types.NoSuchKey
		if errors.As(err, &nsk) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("get %s: %w", key, err)
	}
	return out.Body, nil
}

// Delete removes the object (no error when it is already gone).
func (c *Client) Delete(ctx context.Context, key string) error {
	_, err := c.s3.DeleteObject(ctx, &s3.DeleteObjectInput{Bucket: &c.bucket, Key: &key})
	return err
}

// List returns at most `limit` keys under prefix (bounded; page with a continuation token for
// more).
func (c *Client) List(ctx context.Context, prefix string, limit int32) ([]string, error) {
	out, err := c.s3.ListObjectsV2(ctx, &s3.ListObjectsV2Input{
		Bucket:  &c.bucket,
		Prefix:  &prefix,
		MaxKeys: &limit,
	})
	if err != nil {
		return nil, err
	}

	keys := make([]string, 0, len(out.Contents))
	for _, o := range out.Contents {
		keys = append(keys, aws.ToString(o.Key))
	}
	return keys, nil
}

// IsNotFound reports a missing bucket or key from any SDK error shape.
func IsNotFound(err error) bool {
	if errors.Is(err, ErrNotFound) {
		return true
	}

	var apiErr smithy.APIError
	if !errors.As(err, &apiErr) {
		return false
	}

	code := apiErr.ErrorCode()

	return code == "NoSuchKey" || code == "NotFound"
}
