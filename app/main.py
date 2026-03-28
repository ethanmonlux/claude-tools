from __future__ import annotations

import hmac

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .middleware import RequestSizeLimitMiddleware
from .models import ResearchRequest, ResearchResponse, ProposalRequest, ProposalResponse
from .deps import get_connector
from .skills import prospect_research, proposal_generator

app = FastAPI(title="Claude Tools", version="1.0.0")
app.add_middleware(RequestSizeLimitMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")


def _verify_key(x_api_key: str = Header(default="")):
    if not hmac.compare_digest(x_api_key, settings.skill_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "connector_mode": settings.connector_mode}


@app.post("/skill/research", response_model=ResearchResponse)
async def research(
    req: ResearchRequest,
    _: None = Depends(_verify_key),
):
    connector = get_connector()
    return await prospect_research.run(
        company_name=req.company_name,
        notes=req.notes,
        connector=connector,
        anthropic_api_key=settings.anthropic_key,
        model=settings.anthropic_model,
    )


@app.post("/skill/proposal", response_model=ProposalResponse)
async def proposal(
    req: ProposalRequest,
    _: None = Depends(_verify_key),
):
    connector = get_connector()
    return await proposal_generator.run(
        company_name=req.company_name,
        prospect_data=req.prospect_data,
        connector=connector,
        anthropic_api_key=settings.anthropic_key,
        model=settings.anthropic_model,
    )
