import requests
import time
import logging
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Define the list of anime images
anime_images = [
    "D:\\ai\\DIROL_api\\anime\\01.png",
    "D:\\ai\\DIROL_api\\anime\\2.png",
    "D:\\ai\\DIROL_api\\anime\\3.png",
    "D:\\ai\\DIROL_api\\anime\\4.png",
    "D:\\ai\\DIROL_api\\anime\\5.png",
    "D:\\ai\\DIROL_api\\anime\\6.png",
    "D:\\ai\\DIROL_api\\anime\\7.png",
    "D:\\ai\\DIROL_api\\anime\\8.png"
]

# Define the URLs and headers for the requests
generate_url = "http://194.190.77.197:8881/generate"
history_url_template = "http://194.190.77.197:8882/history/{}"
upload_url = "http://194.190.77.197:8881/uploadfile"
files_base_url = "http://194.190.77.197:8884/files"
headers = {
    "Content-Type": "application/json"
}

# Function to check the status of the prompt and retrieve the filename
def check_status(prompt_id, timeout=100, interval=1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(history_url_template.format(prompt_id))
        if response.status_code == 200:
            response_json = response.json()
            prompt_info = response_json.get(prompt_id, {})
            status_info = prompt_info.get('status', {})
            status = status_info.get('status_str', 'Unknown')
            logging.info(f"Status of prompt {prompt_id}: {status}")
            if status == 'success':
                outputs = prompt_info.get('outputs', {})
                images_info = outputs.get('90', {}).get('images', [])
                if images_info:
                    filename = images_info[0].get('filename')
                    return filename
                return True
            elif status == 'failed':
                return False
        else:
            logging.error(f"Failed to get status for {prompt_id}: {response.status_code} {response.text}")
        time.sleep(interval)
    return False

# Function to upload a file to the server
def upload_file(file):
    response = requests.post(upload_url, files={'file': file})
    if response.status_code == 200:
        response_data = response.json()
        # Construct the full path on the server
        server_file_path = os.path.join("D:\\ai\\Dirol_api\\uploads", response_data['filename'])
        return server_file_path
    else:
        logging.error(f"Failed to upload file: {response.status_code} {response.text}")
        return None

@app.post("/generate_image/")
async def generate_image(anime_index: int = Form(...), girl_image: UploadFile = File(...)):
    if not (0 <= anime_index - 1 < len(anime_images)):
        raise HTTPException(status_code=400, detail=f"Invalid anime_index. Must be between 1 and {len(anime_images)}")
    
    anime_image = anime_images[anime_index - 1]
    logging.info(f"Using anime image: {anime_image}")
    logging.info(f"Uploading girl image: {girl_image.filename}")

    # Upload the girl image
    girl_image_path = upload_file(girl_image.file)
    if not girl_image_path:
        raise HTTPException(status_code=500, detail="Failed to upload girl image")

    logging.info(f"Uploaded girl image path: {girl_image_path}")

    # Define the payload for the POST request
    payload = {
        "image_path1": anime_image,
        "image_path2": girl_image_path
    }

    # Make the POST request
    response = requests.post(generate_url, headers=headers, json=payload)
    response_data = response.json()

    if response.status_code == 200:
        prompt_id = response_data.get('prompt_id')
        if prompt_id:
            logging.info(f"Generated prompt ID: {prompt_id}")
            # Check the status of the prompt and retrieve the filename
            result = check_status(prompt_id)
            if result is True:
                logging.info(f"Prompt {prompt_id} completed successfully but no filename found.")
                raise HTTPException(status_code=500, detail="No filename found in the successful prompt")
            elif result:
                file_url = f"{files_base_url}/{result}"
                logging.info(f"Prompt {prompt_id} completed successfully. File URL: {file_url}")
                return JSONResponse(content={"file_url": file_url})
            else:
                logging.error(f"Prompt {prompt_id} failed or timed out.")
                raise HTTPException(status_code=500, detail="Image generation failed or timed out")
        else:
            logging.error("No prompt_id found in the response.")
            raise HTTPException(status_code=500, detail="No prompt_id found in the response")
    else:
        logging.error(f"Failed to generate image: {response.status_code} {response_data.get('error')}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {response_data.get('error')}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)