import boto3
import json
import os

class MessageQueue:
    def send_message(self, queue_url, message_body):
        raise NotImplementedError

class SqsMessageQueue(MessageQueue):
    def __init__(self):
        self._sqs = None

    @property
    def sqs(self):
        if self._sqs is None:
            self._sqs = boto3.client("sqs")
        return self._sqs

    def send_message(self, queue_url, message_body):
        self.sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))