try:
    from .client import (
        EventPublisher,
        EventSubscriber,
        Msg,
        NatsConnection,
        PullStreamWorker,
        QueueWorker,
        Responder,
        StreamPublisher,
        SubscribeStreamWorker,
    )
except ImportError as e:
    raise ImportError(
        "NATS 模块未安装，请使用 `pip install pocket[nats]` 安装可选依赖"
    ) from e

__all__ = [
    "NatsConnection",
    "EventPublisher",
    "EventSubscriber",
    "Msg",
    "StreamPublisher",
    "PullStreamWorker",
    "SubscribeStreamWorker",
    "QueueWorker",
    "Responder",
]
