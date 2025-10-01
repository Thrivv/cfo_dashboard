import requests
import time

API_KEY = "rpa_KN3HAWGAIXJVZPKFL7WD5JV8XYIZW27LWYZC2RYZ1wthhi"
ENDPOINT_ID = "lkbk4plvvt0vah"
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def run_rag_job(prompt, sampling_params=None):
    """
    Submit a job to the RAG RunPod serverless endpoint.
    
    Args:
        prompt (str): User query or knowledge question
        sampling_params (dict): Optional dict for temperature, max_tokens, etc.
    """
    data = {
        "input": {
            "prompt": prompt,
            "application": "RAG"
        }
    }

    if sampling_params:
        data["input"]["sampling_params"] = sampling_params

    # Step 1: Submit the job
    response = requests.post(f"{BASE_URL}/run", headers=headers, json=data)
    job = response.json()
    job_id = job["id"]

    # Step 2: Poll for the result
    while True:
        status_response = requests.get(f"{BASE_URL}/status/{job_id}", headers=headers)
        status_json = status_response.json()

        if status_json["status"] == "COMPLETED":
            print(f"=== RAG Result ===")
            print(status_json["output"])
            break
        elif status_json["status"] == "FAILED":
            print("Job failed:", status_json)
            break
        else:
            time.sleep(1)
