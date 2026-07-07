import logging
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from apps.token import (
    logger,
    supported_user_agents,
    token_generator,
)
from apps.token.TokenGenerator import get_timezone_from_ip

router = APIRouter()


@router.get("/v1/token")
def v1_token_route(
    request: Request,
    user_agent: Annotated[
        str | None, Query(description="User agent string for token generation")
    ] = None,
    timezone: Annotated[
        str | None, Query(description="IANA timezone ID for token generation")
    ] = None,
):
    """
    Generate a Blackbox token for the specified user agent.
    NOTE: Synchronous to avoid conflicts with sync Playwright code

    Args:
        request: The FastAPI request object to resolve client IP
        user_agent: The user agent string to generate a token for (optional)
        timezone: The IANA timezone ID to use for the token generation (optional, resolved via IP if omitted)

    Returns:
        str: The generated Blackbox token string

    Raises:
        HTTPException: 400 if user_agent is invalid or unsupported
        HTTPException: 500 if token generation fails
    """
    try:
        # If user_agent is None or empty, use default (random) user agent
        if user_agent and user_agent != "" and user_agent not in supported_user_agents:
            raise HTTPException(
                status_code=400,
                detail="Bad Request: Unsupported user_agent query parameter",
            )

        # Resolve timezone dynamically if not passed
        effective_timezone = timezone
        if not effective_timezone:
            # Check X-Forwarded-For behind reverse proxies (like Render / Cloudflare)
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else None
            
            effective_timezone = get_timezone_from_ip(client_ip)

        start_time = time.time()
        token_string = token_generator.get_token(user_agent, effective_timezone)
        processing_time = time.time() - start_time

        return token_string
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in v1_token route")
        raise HTTPException(
            status_code=500, detail="An error occurred during token generation"
        )
