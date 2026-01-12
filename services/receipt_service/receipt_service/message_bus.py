import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Callable, List
import boto3

logger = logging.getLogger(__name__)

class MessageBus(ABC):
    """Abstract base class for message bus implementations."""

    @abstractmethod
    def publish(self, event_type: str, data: Dict):
        """Publish an event to the message bus."""
        pass

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type."""
        pass


class SNSMessageBus(MessageBus):
    """Message bus implementation using AWS SNS."""

    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        self.sns = boto3.client('sns', region_name=self.region)
        self.handlers = {}

    def publish(self, event_type: str, data: Dict):
        """Publish event to SNS topic."""
        if not self.sns_topic_arn:
            logger.warning("SNS_TOPIC_ARN not configured, logging event only")
            logger.info(f"Event: {event_type} - {data}")
            return

        try:
            message = {
                'event_type': event_type,
                'timestamp': data.get('timestamp', ''),
                'data': data
            }

            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Message=json.dumps(message),
                MessageAttributes={
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': event_type
                    }
                }
            )
            logger.info(f"Event published to SNS: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    def subscribe(self, event_type: str, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Handler registered for event: {event_type}")


class LocalMessageBus(MessageBus):
    """Local in-memory message bus for development."""

    def __init__(self):
        self.handlers = {}
        logger.info("Using LocalMessageBus (development mode)")

    def publish(self, event_type: str, data: Dict):
        """Publish event locally (just log it)."""
        logger.info(f"[EVENT] {event_type}: {data}")

        # Call registered handlers
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")

    def subscribe(self, event_type: str, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Handler registered for event: {event_type}")


def get_message_bus() -> MessageBus:
    """Factory function to get the appropriate message bus."""
    env = os.getenv('FLASK_ENV', 'dev')

    if env == 'prod':
        return SNSMessageBus()
    else:
        return LocalMessageBus()
