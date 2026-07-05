from fastapi import APIRouter
from pydantic import BaseModel

from app.chat.agent import ask_about_job_status

router = APIRouter(prefix="/chat", tags=["chat"])


class JobStatusQuestion(BaseModel):
    question: str


class JobStatusAnswer(BaseModel):
    answer: str


@router.post("/job-status", response_model=JobStatusAnswer)
async def job_status_chat(data: JobStatusQuestion) -> JobStatusAnswer:
    answer = await ask_about_job_status(data.question)
    return JobStatusAnswer(answer=answer)
