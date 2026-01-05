"""
Realtime WebSocket broadcaster.
Listens to Kafka topics and broadcasts events to connected WebSocket clients.
"""
import json
import threading
from typing import List
from kafka import KafkaConsumer
from fastapi import WebSocket

from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_COMPLETED_TOPIC, KAFKA_PENDING_TOPIC, KAFKA_API_VERSION
from src.logging import setup_logger

logger = setup_logger("realtime")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


def _kafka_listener_thread():
    """Background thread reading Kafka topics and broadcasting messages."""
    try:
        consumer = KafkaConsumer(
            KAFKA_COMPLETED_TOPIC,
            KAFKA_PENDING_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            api_version=KAFKA_API_VERSION,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        logger.info("Kafka realtime consumer started")

        for msg in consumer:
            topic = msg.topic
            payload = msg.value
            event = {
                "topic": topic,
                "payload": payload
            }
            # Use async broadcast via loop
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # schedule broadcast
                coro = manager.broadcast(event)
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                # fallback: no loop running
                logger.debug("Event received but event loop not running")
    except Exception as e:
        logger.error(f"Realtime Kafka listener error: {str(e)}")


def start_realtime_listener():
    t = threading.Thread(target=_kafka_listener_thread, daemon=True)
    t.start()
    logger.info("Realtime listener thread launched")
