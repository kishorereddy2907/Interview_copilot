import os
import requests
import zipfile
import shutil

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_ZIP = "vosk-model.zip"
EXTRACT_DIR = "."
FINAL_DIR = "vosk_model"

def setup_vosk():
    if os.path.exists(FINAL_DIR):
        print(f"Directory '{FINAL_DIR}' already exists. Skipping download.")
        return

    print(f"Downloading model from {MODEL_URL}...")
    response = requests.get(MODEL_URL, stream=True)
    with open(MODEL_ZIP, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print("Download complete. Extracting...")
    with zipfile.ZipFile(MODEL_ZIP, "r") as zip_ref:
        zip_ref.extractall(EXTRACT_DIR)
    
    # Rename the extracted folder
    extracted_folder = "vosk-model-small-en-us-0.15"
    if os.path.exists(extracted_folder):
        os.rename(extracted_folder, FINAL_DIR)
        print(f"Model extracted to '{FINAL_DIR}'.")
    else:
        print(f"Error: Expected extracted folder '{extracted_folder}' not found.")

    # Cleanup
    if os.path.exists(MODEL_ZIP):
        os.remove(MODEL_ZIP)
    print("Setup complete.")

if __name__ == "__main__":
    setup_vosk()
