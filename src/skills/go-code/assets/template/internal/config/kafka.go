package config

import "strings"

// Kafka is loaded from KAFKA_BOOTSTRAP_SERVERS, KAFKA_SECURITY_PROTOCOL, KAFKA_SASL_MECHANISM,
// KAFKA_SASL_USERNAME, KAFKA_SASL_PASSWORD[_FILE] (required for SASL_*) and KAFKA_CONSUMER_GROUP
// (see kafka.env.example in go-kafka).
type Kafka struct {
	BootstrapServers string
	SecurityProtocol string
	SASLMechanism    string
	SASLUsername     string
	SASLPassword     string
	ConsumerGroup    string
}

// LoadKafka reads the KAFKA_* variables and validates SASL credentials against the security
// protocol.
func LoadKafka(l *Loader) Kafka {
	k := Kafka{
		BootstrapServers: l.Req("KAFKA_BOOTSTRAP_SERVERS"),
		SecurityProtocol: strings.ToUpper(l.Str("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")),
		SASLMechanism:    l.Str("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256"),
		SASLUsername:     l.Str("KAFKA_SASL_USERNAME", ""),
		SASLPassword:     l.OptSecret("KAFKA_SASL_PASSWORD"),
		ConsumerGroup:    l.Req("KAFKA_CONSUMER_GROUP"),
	}

	usesSASL := strings.HasPrefix(k.SecurityProtocol, "SASL_")
	missingCredentials := k.SASLUsername == "" || k.SASLPassword == ""

	if usesSASL && missingCredentials {
		l.Fail(
			"KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD (or _FILE) are required "+
				"when KAFKA_SECURITY_PROTOCOL is %s",
			k.SecurityProtocol,
		)
	}

	return k
}
