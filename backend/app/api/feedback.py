from fastapi import APIRouter, HTTPException

from app.models.schemas import FeedbackRequest
from app.services.feedback_store import FeedbackStore

router = APIRouter(prefix="/feedback", tags=["feedback"])
feedback_store = FeedbackStore("data/feedback.json")


@router.post("")
async def submit_feedback(request: FeedbackRequest) -> dict[str, str]:
    try:
        feedback_store.append(trace_id=request.trace_id, vote=request.vote, comment=request.comment)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {exc}") from exc
