use super::Loader;

/// KAFKA_BOOTSTRAP_SERVERS, KAFKA_SECURITY_PROTOCOL, KAFKA_SASL_MECHANISM, KAFKA_SASL_USERNAME,
/// KAFKA_SASL_PASSWORD[_FILE] (required for SASL_*), KAFKA_CONSUMER_GROUP (see kafka.env.example).
#[derive(Clone)]
pub struct Kafka {
    pub bootstrap_servers: String,
    pub security_protocol: String,
    pub sasl_mechanism: String,
    pub sasl_username: String,
    pub sasl_password: String,
    pub consumer_group: String,
}

impl Kafka {
    pub fn load(l: &mut Loader) -> Kafka {
        let k = Kafka {
            bootstrap_servers: l.req("KAFKA_BOOTSTRAP_SERVERS"),
            security_protocol: l.str("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT").to_uppercase(),
            sasl_mechanism: l.str("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256"),
            sasl_username: l.str("KAFKA_SASL_USERNAME", ""),
            sasl_password: l.opt_secret("KAFKA_SASL_PASSWORD"),
            consumer_group: l.req("KAFKA_CONSUMER_GROUP"),
        };
        if k.security_protocol.starts_with("SASL_")
            && (k.sasl_username.is_empty() || k.sasl_password.is_empty())
        {
            l.fail(format!(
                "KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD (or _FILE) are required \
                 when KAFKA_SECURITY_PROTOCOL is {}",
                k.security_protocol
            ));
        }
        k
    }

    /// librdkafka client settings every producer and consumer needs (add them to rdkafka's
    /// `ClientConfig`).
    pub fn client_config(&self) -> Vec<(&'static str, String)> {
        let mut c = vec![
            ("bootstrap.servers", self.bootstrap_servers.clone()),
            ("security.protocol", self.security_protocol.clone()),
        ];
        if self.security_protocol.starts_with("SASL_") {
            c.push(("sasl.mechanism", self.sasl_mechanism.clone()));
            c.push(("sasl.username", self.sasl_username.clone()));
            c.push(("sasl.password", self.sasl_password.clone()));
        }
        c
    }
}
