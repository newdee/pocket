import asyncio
from abc import abstractmethod
from typing import Awaitable, Callable, Self, TypeAlias

import nats
from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js import JetStreamContext

from ..logger import logger

Msg: TypeAlias = Msg


class NatsConnection:
    nc: Client
    js: JetStreamContext

    def __init__(self, server: str, nc: Client, js: JetStreamContext) -> None:
        self.server = server
        self.nc = nc
        self.js = js

    @classmethod
    async def create(cls, server: str = "nats://127.0.0.1:4222") -> Self:
        logger.info(f"[NATS] Connecting to {server}")
        nc = await nats.connect(server)
        js = nc.jetstream()
        logger.success("[NATS] Connected and JetStream ready")
        return cls(server, nc, js)

    async def close(self) -> None:
        logger.info("[NATS] Draining connection")
        await self.nc.drain()
        logger.success("[NATS] Connection closed")

    async def request(self, subject: str, data: bytes, timeout: float = 1.0) -> bytes:
        logger.info(f"[REQUEST] Sending request to {subject}")
        msg = await self.nc.request(subject, data, timeout=timeout)
        logger.info(f"[REQUEST] Received reply from {subject}")
        return msg.data


class EventPublisher:
    def __init__(self, conn: NatsConnection) -> None:
        self.nc = conn.nc

    async def publish(self, subject: str, data: bytes) -> None:
        logger.debug(f"[EVENT:PUB] {subject} -> {data!r}")
        await self.nc.publish(subject, data)
        logger.info(f"[EVENT:PUB] Sent to {subject}")


class EventSubscriber:
    def __init__(self, conn: NatsConnection) -> None:
        self.nc = conn.nc

    async def subscribe(
        self,
        subject: str,
        handler: Callable[[Msg], Awaitable[None]],
    ) -> None:
        logger.info(f"[EVENT:SUB] Subscribing to {subject}")
        await self.nc.subscribe(subject, cb=handler)
        logger.success(f"[EVENT:SUB] Listening on {subject}")


class StreamPublisher:
    def __init__(self, conn: NatsConnection, stream: str, subject: str) -> None:
        self.js = conn.js
        self.stream = stream
        self.subject = subject

    async def init_stream(self) -> None:
        """初始化 stream，如果不存在则创建"""
        logger.info(
            f"[WORKER] Initializing stream={self.stream} subject={self.subject}"
        )
        try:
            await self.js.add_stream(name=self.stream, subjects=[self.subject])
            logger.success(f"[WORKER] Stream ready: {self.stream} -> {self.subject}")
        except Exception as e:
            logger.warning(f"[WORKER] Stream may already exist: {e}")

    async def submit(self, data: bytes) -> None:
        logger.info(f"[QUEUE:PUB] Submit task -> {self.subject}")
        ack = await self.js.publish(self.subject, data)
        logger.success(f"[QUEUE:PUB] Stored seq={ack.seq} subject={self.subject}")


class BaseStreamWorker:
    def __init__(
        self, *, conn: NatsConnection, stream: str, subject: str, durable: str
    ) -> None:
        self.js = conn.js
        self.stream = stream
        self.subject = subject
        self.durable = durable

    async def init_stream(self) -> None:
        """初始化 stream，如果不存在则创建"""
        logger.info(
            f"[WORKER] Initializing stream={self.stream} subject={self.subject}"
        )
        try:
            await self.js.add_stream(name=self.stream, subjects=[self.subject])
            logger.success(f"[WORKER] Stream ready: {self.stream} -> {self.subject}")
        except Exception as e:
            logger.warning(f"[WORKER] Stream may already exist: {e}")

    @abstractmethod
    async def run(self, handler: Callable[[Msg], Awaitable[None]]) -> None: ...


class PullStreamWorker(BaseStreamWorker):
    def __init__(
        self,
        conn: NatsConnection,
        stream: str,
        subject: str,
        durable: str,
        batch: int = 1,
    ) -> None:
        super().__init__(conn=conn, stream=stream, subject=subject, durable=durable)
        self.batch = batch

    async def run(self, handler: Callable[[Msg], Awaitable[None]]) -> None:
        logger.info(
            f"[WORKER] Starting worker durable={self.durable} subject={self.subject}"
        )
        sub = await self.js.pull_subscribe(
            subject=self.subject,
            durable=self.durable,
        )

        logger.success(f"[WORKER] Ready (durable={self.durable})")

        while True:
            try:
                msgs = await sub.fetch(self.batch)
            except asyncio.TimeoutError:
                continue

            for msg in msgs:
                logger.info(f"[WORKER] Got task seq={msg.metadata.sequence.stream}")

                try:
                    await handler(msg)
                    await msg.ack()
                    logger.success(f"[WORKER] Acked seq={msg.metadata.sequence.stream}")
                except Exception as e:
                    logger.error(
                        f"[WORKER] Failed seq={msg.metadata.sequence.stream}: {e}"
                    )
                    await msg.nak()


class SubscribeStreamWorker(BaseStreamWorker):
    def __init__(
        self,
        conn: NatsConnection,
        stream: str,
        subject: str,
        durable: str,
    ) -> None:
        super().__init__(conn=conn, stream=stream, subject=subject, durable=durable)

    async def run(self, handler: Callable[[Msg], Awaitable[None]]) -> None:
        logger.info(
            f"[WORKER] Starting subscribe worker durable={self.durable} subject={self.subject}"
        )

        await self.js.subscribe(subject=self.subject, durable=self.durable, cb=handler)

        logger.success(f"[WORKER] Listening (durable={self.durable}) on {self.subject}")


class QueueWorker:
    def __init__(
        self,
        conn: NatsConnection,
        subject: str,
        queue: str,
    ) -> None:
        self.nc = conn.nc
        self.subject = subject
        self.queue = queue

    async def run(self, handler: Callable[[Msg], Awaitable[None]]) -> None:
        logger.info(f"[QUEUE] Starting worker on {self.subject} (queue={self.queue})")

        await self.nc.subscribe(
            self.subject,
            cb=handler,
            queue=self.queue,
        )

        logger.success(f"[QUEUE] Listening on {self.subject} (queue={self.queue})")


class Responder:
    def __init__(self, conn: NatsConnection, subject: str) -> None:
        self.nc = conn.nc
        self.subject = subject

    async def serve(self, handler: Callable[[Msg], Awaitable[None]]) -> None:
        async def cb(msg: Msg):
            try:
                await handler(msg)
            except Exception as e:
                logger.error(f"Error in responder callback: {e}")

        logger.info(f"[RESPONDER] Subscribing to {self.subject}")
        await self.nc.subscribe(self.subject, cb=cb)
        logger.success(f"[RESPONDER] Listening on {self.subject}")
