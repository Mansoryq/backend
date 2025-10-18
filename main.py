from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import asyncio  

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    
HF_API_KEY = "93b61826-44b8-427e-addd-9744bfda8d32"
HF_SECRET = "a39ac8a8a3e77de51946842692e413a9f5f646e6fa36579e76acd5bd21e8cc7b"

@app.post("/generate")
async def generate(prompt: str):
        url = "https://platform.higgsfield.ai/v1/models/nano-banana/generations"
        headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
        data = {"params": {"prompt": prompt}}
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {response.text}")
        job_id = response.json().get("job_id")
        if not job_id:
            raise HTTPException(status_code=500, detail="No job_id in image response")

        for _ in range(60):
            await asyncio.sleep(5)
            status_url = f"https://platform.higgsfield.ai/v1/job-sets/{job_id}"
            try:
                status_response = requests.get(status_url, headers=headers)
                status = status_response.json()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
            if status.get("status") == "completed":
                image_url = status["result"]["url"]
                break
            elif status.get("status") == "failed":
                raise HTTPException(status_code=500, detail="Image generation failed")
        else:
            raise HTTPException(status_code=500, detail="Image generation timeout")

        
        video_url = "https://platform.higgsfield.ai/v1/models/kling-2-5/generations"
        video_data = {"params": {"image_url": image_url, "duration": 5}}  # Добавьте другие params если нужно
        video_response = requests.post(video_url, json=video_data, headers=headers)
        if video_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Video generation failed: {video_response.text}")
        video_job_id = video_response.json().get("job_id")
        if not video_job_id:
            raise HTTPException(status_code=500, detail="No job_id in video response")

        
        for _ in range(60):
            await asyncio.sleep(5)
            video_status_url = f"https://platform.higgsfield.ai/v1/job-sets/{video_job_id}"
            try:
                video_status_response = requests.get(video_status_url, headers=headers)
                video_status = video_status_response.json()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Video status check failed: {str(e)}")
            if video_status.get("status") == "completed":
                video_result_url = video_status["result"]["url"]
                return {"image": image_url, "video": video_result_url}
            elif video_status.get("status") == "failed":
                raise HTTPException(status_code=500, detail="Video generation failed")
        else:
            raise HTTPException(status_code=500, detail="Video generation timeout")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    