// Package kafkax wraps confluent-kafka-go v2 (cgo, bundled librdkafka): a durable producer and a
// manual-commit consumer loop.
package kafkax

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"

	"example.com/service/internal/application"
	"example.com/service/internal/config"
)

var _ application.EventPublisher = (*Producer)(nil)

// Producer publishes messages and waits for the broker acknowledgement.
type Producer struct {
	p *kafka.Producer
}

// baseConfig holds what every client needs; SASL settings are added only for SASL_* protocols.
func baseConfig(c config.Kafka) *kafka.ConfigMap {
	cm := &kafka.ConfigMap{
		"bootstrap.servers": c.BootstrapServers,
		"security.protocol": c.SecurityProtocol,
	}

	if strings.HasPrefix(c.SecurityProtocol, "SASL_") {
		_ = cm.SetKey("sasl.mechanism", c.SASLMechanism)
		_ = cm.SetKey("sasl.username", c.SASLUsername)
		_ = cm.SetKey("sasl.password", c.SASLPassword)
	}

	return cm
}

// NewProducer is idempotent and waits for all in-sync replicas: no duplicates on retry, no silent
// loss.
func NewProducer(c config.Kafka) (*Producer, error) {
	cm := baseConfig(c)

	settings := map[string]kafka.ConfigValue{
		"enable.idempotence": true,
		"acks":               "all",
		"linger.ms":          5,
		"compression.type":   "lz4",
	}
	for k, v := range settings {
		_ = cm.SetKey(k, v)
	}

	p, err := kafka.NewProducer(cm)
	if err != nil {
		return nil, fmt.Errorf("kafka producer: %w", err)
	}
	return &Producer{p: p}, nil
}

// Publish waits for the delivery report (or ctx): the caller learns whether the broker
// acknowledged.
func (p *Producer) Publish(ctx context.Context, topic, key string, value []byte) error {
	done := make(chan kafka.Event, 1)
	msg := &kafka.Message{
		TopicPartition: kafka.TopicPartition{
			Topic:     &topic,
			Partition: kafka.PartitionAny,
		},
		Key:   []byte(key),
		Value: value,
	}

	if err := p.p.Produce(msg, done); err != nil {
		return fmt.Errorf("produce %s: %w", topic, err)
	}

	select {
	case ev := <-done:
		if m, ok := ev.(*kafka.Message); ok && m.TopicPartition.Error != nil {
			return fmt.Errorf("deliver %s: %w", topic, m.TopicPartition.Error)
		}
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Ping checks that the cluster answers a metadata request.
func (p *Producer) Ping(ctx context.Context) error {
	_, err := p.p.GetMetadata(nil, false, 3000)
	return err
}

// Close drains queued messages (bounded) before closing.
func (p *Producer) Close() {
	p.p.Flush(10_000)
	p.p.Close()
}

// Handler processes one message; returning nil lets the consumer commit its offset.
type Handler func(ctx context.Context, m *kafka.Message) error

// Consume runs until ctx is cancelled. A message is committed only after the handler succeeds, so a
// crash re-delivers it: handlers must be idempotent. A handler error stops the loop (the caller
// decides: retry, DLQ).
func Consume(ctx context.Context, c config.Kafka, topics []string, h Handler) error {
	cm := baseConfig(c)

	settings := map[string]kafka.ConfigValue{
		"group.id":           c.ConsumerGroup,
		"enable.auto.commit": false,
		"auto.offset.reset":  "latest",
	}
	for k, v := range settings {
		_ = cm.SetKey(k, v)
	}

	cons, err := kafka.NewConsumer(cm)
	if err != nil {
		return fmt.Errorf("kafka consumer: %w", err)
	}
	defer func() {
		_ = cons.Close()
	}()

	if err := cons.SubscribeTopics(topics, nil); err != nil {
		return err
	}
	for ctx.Err() == nil {
		ev, err := cons.ReadMessage(500 * time.Millisecond)
		if err != nil {
			var kerr kafka.Error
			if errors.As(err, &kerr) && kerr.Code() == kafka.ErrTimedOut {
				continue
			}
			return err
		}
		if err := h(ctx, ev); err != nil {
			part := ev.TopicPartition

			return fmt.Errorf("handle %s[%d]@%d: %w", *part.Topic, part.Partition, part.Offset, err)
		}
		if _, err := cons.CommitMessage(ev); err != nil {
			return err
		}
	}
	return nil
}
