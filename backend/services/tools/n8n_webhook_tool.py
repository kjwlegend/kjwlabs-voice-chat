"""
N8N Webhook Tool for KJW Labs Voice Chat System

This tool integrates with N8N workflows via webhooks to execute various automation tasks.
Supports secure HTTP requests with retry logic and comprehensive error handling.
"""

import json
import logging
import time
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .tool_base import ToolBase, ToolParameter, ToolResult, ParameterType

# Configure logging
logger = logging.getLogger(__name__)


class N8NWebhookTool(ToolBase):
    """
    N8N Webhook Tool for executing workflow automations

    This tool sends HTTP requests to N8N webhook endpoints to trigger workflows
    and automation tasks. It includes retry logic, timeout handling, and
    comprehensive error management.
    """

    def __init__(
        self,
        webhook_url: str = "https://kai.kjwlabs.com/webhook/n8n",
        execution_mode: str = "production",
        timeout: int = 30,
    ):
        """
        Initialize the N8N Webhook Tool

        Args:
            webhook_url: The N8N webhook URL (default: https://kai.kjwlabs.com/webhook/n8n)
            execution_mode: The execution mode (default: production)
            timeout: Request timeout in seconds (default: 30)
        """
        super().__init__(
            name="n8n_webhook",
            description="Execute N8N workflow automations via webhook. Send queries to trigger various automation tasks like email sending, data processing, notifications, etc.",
        )

        self.webhook_url = webhook_url
        self.execution_mode = execution_mode
        self.timeout = timeout

        # Configure HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Define tool parameters
        self._define_parameters()

        logger.info(f"N8N Webhook Tool initialized with URL: {self.webhook_url}")

    def _define_parameters(self):
        """Define tool parameters with validation"""
        self.add_parameter(
            ToolParameter(
                name="query",
                type=ParameterType.STRING,
                description="The query or instruction to send to N8N workflow. This should be a clear, descriptive request for the automation task you want to execute.",
                required=True,
            )
        )

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the N8N webhook request

        Args:
            parameters: Tool parameters including query

        Returns:
            ToolResult with execution results
        """
        try:
            # Extract query parameter
            query = parameters.get("query", "")

            # Construct request payload according to user's format
            payload = {
                "query": query,
                "webhookUrl": self.webhook_url,
                "executionMode": self.execution_mode,
            }

            logger.info(f"Sending N8N webhook request with query: {query[:100]}...")
            logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

            # Record start time for performance tracking
            start_time = time.time()

            # Make the HTTP request
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "KJW-Labs-Voice-Chat/1.0",
                },
            )

            # Calculate execution time
            execution_time = time.time() - start_time

            # Log response details
            logger.info(
                f"N8N webhook response: {response.status_code} in {execution_time:.2f}s"
            )
            logger.debug(f"Response headers: {dict(response.headers)}")

            # Handle response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info("N8N webhook executed successfully")

                    return ToolResult(
                        success=True,
                        data={
                            "status": "success",
                            "response": response_data,
                            "execution_time": execution_time,
                            "query": query,
                        },
                        execution_time=execution_time,
                    )
                except json.JSONDecodeError:
                    # Handle non-JSON response
                    response_text = response.text
                    logger.info(
                        f"N8N webhook returned non-JSON response: {response_text[:200]}..."
                    )

                    return ToolResult(
                        success=True,
                        data={
                            "status": "success",
                            "response": response_text,
                            "execution_time": execution_time,
                            "query": query,
                        },
                        execution_time=execution_time,
                    )
            else:
                # Handle HTTP errors
                error_msg = f"N8N webhook failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)

                return ToolResult(
                    success=False,
                    error=error_msg,
                    data={
                        "status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                        "execution_time": execution_time,
                        "query": query,
                    },
                    execution_time=execution_time,
                )

        except requests.exceptions.Timeout:
            error_msg = f"N8N webhook request timed out after {self.timeout}s"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                data={"status": "timeout", "timeout": self.timeout},
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"N8N webhook request failed: {str(e)}"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                data={"status": "request_error", "error": str(e)},
            )

        except Exception as e:
            error_msg = f"Unexpected error in N8N webhook tool: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg,
                data={"status": "unexpected_error", "error": str(e)},
            )

    def __repr__(self) -> str:
        return f"N8NWebhookTool(url={self.webhook_url}, mode={self.execution_mode})"
