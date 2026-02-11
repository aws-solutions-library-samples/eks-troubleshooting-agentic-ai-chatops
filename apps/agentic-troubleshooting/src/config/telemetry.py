"""Telemetry configuration for Langfuse integration."""

import os
import base64
import logging
from strands.telemetry import StrandsTelemetry
from src.config.settings import Config

logger = logging.getLogger(__name__)


def setup_langfuse_telemetry():
    """Configure and initialize Langfuse telemetry."""
    if not Config.ENABLE_LANGFUSE:
        logger.info("Langfuse telemetry disabled")
        return None
    
    # Set Langfuse environment variables
    os.environ["LANGFUSE_SECRET_KEY"] = Config.LANGFUSE_SECRET_KEY
    os.environ["LANGFUSE_PUBLIC_KEY"] = Config.LANGFUSE_PUBLIC_KEY
    os.environ["LANGFUSE_HOST"] = Config.LANGFUSE_HOST
    
    # Set up OpenTelemetry endpoint
    otel_endpoint = f"{Config.LANGFUSE_HOST}/api/public/otel"
    logger.info(f"Configuring OTEL endpoint: {otel_endpoint}")
    
    # Create authentication token
    auth_token = base64.b64encode(
        f"{Config.LANGFUSE_PUBLIC_KEY}:{Config.LANGFUSE_SECRET_KEY}".encode()
    ).decode()
    
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otel_endpoint
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_token}"
    os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
    
    # Initialize Strands telemetry
    telemetry = StrandsTelemetry().setup_otlp_exporter()
    logger.info("Langfuse telemetry initialized successfully")
    
    return telemetry
