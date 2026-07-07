import logging
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Annotated

from apps.token import (
    logger,
    supported_user_agents,
    token_generator,
)

router = APIRouter()

TOKEN_PAGE_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<script src="https://gameforge.com/tra/game1.js"></script>
<script>
function handleToken(token) {
    var element = document.createElement("div");
    element.textContent = token;
    document.body.appendChild(element);
}
game1(handleToken);
</script>
</body>
</html>"""


@router.get("/v1/token-page", response_class=HTMLResponse)
async def token_page():
    return TOKEN_PAGE_HTML


@router.get("/v1/token")
def v1_token_route(
    user_agent: Annotated[
        str | None, Query(description="User agent string for token generation")
    ] = None,
):
    try:
        if user_agent and user_agent != "" and user_agent not in supported_user_agents:
            raise HTTPException(
                status_code=400,
                detail="Bad Request: Unsupported user_agent query parameter",
            )

        import time
        start_time = time.time()
        token_string = token_generator.get_token(user_agent)
        processing_time = time.time() - start_time

        logger.info(f"Token generated in {processing_time:.2f}s, length={len(token_string)}")

        return token_string
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in v1_token route")
        raise HTTPException(
            status_code=500, detail="An error occurred during token generation"
        )
