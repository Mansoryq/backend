from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HF_API_KEY = os.getenv("HF_API_KEY")
HF_SECRET = os.getenv("HF_SECRET")
    

@app.post("/generate")
async def generate(prompt: str):
    
    url = "https://platform.higgsfield.ai/v1/models/nano-banana/generations"
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    data = {"params": {"prompt": prompt}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Image generation failed")
    job_id = response.json()["job_id"]
    
    
    while True:
        status_url = f"https://platform.higgsfield.ai/v1/job-sets/{job_id}"
        status = requests.get(status_url, headers=headers).json()
        if status["status"] == "completed":
            image_url = status["result"]["url"]
            break
        time.sleep(5)
    
    
    video_url = "https://platform.higgsfield.ai/v1/models/kling-2-5/generations"
    video_data = {"params": {"image_url": image_url, "duration": 5}} 
    video_response = requests.post(video_url, json=video_data, headers=headers)
    if video_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Video generation failed")
    video_job_id = video_response.json()["job_id"]
    
    
    while True:
        video_status = requests.get(f"https://platform.higgsfield.ai/v1/job-sets/{video_job_id}", headers=headers).json()
        if video_status["status"] == "completed":
            video_result_url = video_status["result"]["url"]
            return {"image": image_url, "video": video_result_url}
        time.sleep(5)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
