from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import asyncio
from typing import Dict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_API_KEY = os.getenv("HF_API_KEY")
HF_SECRET = os.getenv("HF_SECRET")

if not HF_API_KEY or not HF_SECRET:
    raise RuntimeError("HF_API_KEY and HF_SECRET must be set as environment variables!")


jobs: Dict[str, dict] = {}

@app.post("/generate")
async def start_generate(prompt: str):
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    
    
    response = requests.post(
        "https://platform.higgsfield.ai/v1/models/nano-banana/generations",
        json={"params": {"prompt": prompt}},
        headers=headers
    )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Image job start failed")
    
    job_id = response.json()["job_id"]
    jobs[job_id] = {"status": "image_pending", "prompt": prompt}
    
    
    asyncio.create_task(process_job(job_id))
    
    return {"job_id": job_id}

async def process_job(job_id: str):
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    job = jobs[job_id]
    
    
    for _ in range(60):
        await asyncio.sleep(5)
        status_res = requests.get(f"https://platform.higgsfield.ai/v1/job-sets/{job_id}", headers=headers)
        status = status_res.json()
        if status.get("status") == "completed":
            image_url = status["result"]["url"]
            break
        elif status.get("status") == "failed":
            jobs[job_id]["status"] = "failed"
            return
    else:
        jobs[job_id]["status"] = "timeout"
        return

    
    video_res = requests.post(
        "https://platform.higgsfield.ai/v1/models/kling-2-5/generations",
        json={"params": {"image_url": image_url, "duration": 5}},
        headers=headers
    )
    if video_res.status_code != 200:
        jobs[job_id]["status"] = "video_start_failed"
        return

    video_job_id = video_res.json()["job_id"]
    jobs[job_id]["video_job_id"] = video_job_id
    jobs[job_id]["status"] = "video_pending"

    
    for _ in range(60):
        await asyncio.sleep(5)
        video_status_res = requests.get(f"https://platform.higgsfield.ai/v1/job-sets/{video_job_id}", headers=headers)
        video_status = video_status_res.json()
        if video_status.get("status") == "completed":
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["image"] = image_url
            jobs[job_id]["video"] = video_status["result"]["url"]
            return
        elif video_status.get("status") == "failed":
            jobs[job_id]["status"] = "failed"
            return
    else:
        jobs[job_id]["status"] = "timeout"

@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job