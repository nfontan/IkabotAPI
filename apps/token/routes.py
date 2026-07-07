import logging
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from apps.token import (
    logger,
    supported_user_agents,
    token_generator,
)

router = APIRouter()


@router.get("/v1/token")
def v1_token_route(
    user_agent: Annotated[
        str | None, Query(description="User agent string for token generation")
    ] = None,
    locale: Annotated[
        str | None, Query(description="Browser locale (e.g. es-ES)")
    ] = None,
    timezone_id: Annotated[
        str | None, Query(description="Timezone ID (e.g. America/Argentina/Buenos_Aires)")
    ] = None,
):
    try:
        if user_agent and user_agent != "" and user_agent not in supported_user_agents:
            raise HTTPException(
                status_code=400,
                detail="Bad Request: Unsupported user_agent query parameter",
            )

        start_time = time.time()
        token_string = token_generator.get_token(
            user_agent=user_agent,
            locale=locale,
            timezone_id=timezone_id,
        )
        processing_time = time.time() - start_time

        return token_string
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in v1_token route")
        raise HTTPException(
            status_code=500, detail="An error occurred during token generation"
        )
