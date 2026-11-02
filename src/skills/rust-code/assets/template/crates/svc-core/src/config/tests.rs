use std::collections::HashMap;

use super::*;

fn env(extra: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
    let mut m: HashMap<String, String> = [
        ("SERVICE_NAME", "svc"),
        ("INTERNAL_SERVICE_TOKEN", "tok"),
        ("POSTGRES_HOST", "pg"),
        ("POSTGRES_DB", "db"),
        ("POSTGRES_USER", "u"),
        ("POSTGRES_PASSWORD", "p"),
        ("REDIS_HOST", "r"),
        ("REDIS_PASSWORD", "p"),
        ("KAFKA_BOOTSTRAP_SERVERS", "k:9092"),
        ("KAFKA_CONSUMER_GROUP", "g"),
        ("S3_ENDPOINT", "http://s3:9000"),
        ("S3_BUCKET", "b"),
        ("S3_ACCESS_KEY", "a"),
        ("S3_SECRET_KEY", "s"),
    ]
    .iter()
    .map(|(k, v)| (k.to_string(), v.to_string()))
    .collect();
    for (k, v) in extra {
        if v.is_empty() {
            m.remove(*k);
        } else {
            m.insert(k.to_string(), v.to_string());
        }
    }
    move |name| m.get(name).cloned()
}

#[test]
fn loads_defaults() {
    let cfg = load_with(env(&[])).unwrap();
    assert_eq!(
        (cfg.postgres.port, cfg.redis.port, cfg.http_addr().as_str()),
        (5432, 6379, "0.0.0.0:3000")
    );
    assert_eq!(cfg.env_name, "local");
    assert!(cfg.s3.force_path_style);
    assert_eq!(cfg.s3.region, "us-east-1");
}

#[test]
fn every_secret_is_required_by_name() {
    for name in [
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "INTERNAL_SERVICE_TOKEN",
    ] {
        let err = load_with(env(&[(name, "")])).unwrap_err().to_string();
        assert!(err.contains(name), "{name}: {err}");
    }
}

#[test]
fn one_error_lists_every_problem_and_no_values() {
    let err = load_with(env(&[
        ("POSTGRES_HOST", ""),
        ("REDIS_PORT", "x"),
        ("S3_FORCE_PATH_STYLE", "maybe"),
    ]))
    .unwrap_err()
    .to_string();
    for want in ["POSTGRES_HOST", "REDIS_PORT", "S3_FORCE_PATH_STYLE"] {
        assert!(err.contains(want), "{err}");
    }
    assert!(!err.contains("tok"));
}

#[test]
fn debug_output_hides_secrets() {
    let cfg = load_with(env(&[("POSTGRES_PASSWORD", "s3cret")])).unwrap();
    assert!(!format!("{cfg:?}").contains("s3cret"));
}

#[test]
fn kafka_sasl_needs_credentials() {
    assert!(load_with(env(&[("KAFKA_SECURITY_PROTOCOL", "sasl_ssl")]))
        .unwrap_err()
        .to_string()
        .contains("KAFKA_SASL_USERNAME"));
    let cfg = load_with(env(&[
        ("KAFKA_SECURITY_PROTOCOL", "SASL_SSL"),
        ("KAFKA_SASL_USERNAME", "u"),
        ("KAFKA_SASL_PASSWORD", "p"),
    ]))
    .unwrap();
    assert!(cfg
        .kafka
        .client_config()
        .iter()
        .any(|(k, v)| *k == "sasl.username" && v == "u"));
}

/// The env example must load: every variable the loaders read is documented, secrets are blank (no
/// defaults).
#[test]
fn env_example_is_complete() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../.env.example");
    let raw = std::fs::read_to_string(path).unwrap();
    let mut vars = HashMap::new();
    for line in raw
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
    {
        let (k, v) = line.split_once('=').unwrap();
        let secret = k.ends_with("PASSWORD") || k.ends_with("TOKEN") || k.ends_with("KEY");
        assert!(
            !(secret && !v.is_empty()),
            "{k} must be blank: secrets have no default"
        );
        vars.insert(
            k.to_string(),
            if secret {
                "dummy-secret".to_string()
            } else {
                v.to_string()
            },
        );
    }
    load_with(|n| vars.get(n).cloned()).unwrap();
}

#[test]
fn env_name_follows_the_log_format_order() {
    let case = |extra: &[(&str, &str)]| load_with(env(extra)).unwrap().env_name;
    let all = [
        ("DEVELOPMENT_ENVIRONMENT", "dev"),
        ("ENV_NAME", "stg"),
        ("RUN_ENV", "prod"),
    ];
    assert_eq!(case(&all), "dev");
    assert_eq!(case(&all[1..]), "stg");
    assert_eq!(case(&all[2..]), "prod");
}

#[test]
fn public_config_has_no_secrets() {
    let cfg = load_with(env(&[])).unwrap();
    let shown = serde_json::Value::Object(cfg.public()).to_string();
    assert!(shown.contains("3000"));
    for secret in ["tok", "POSTGRES_PASSWORD"] {
        assert!(!shown.contains(secret), "public config shows {secret}");
    }
}
