#!/usr/bin/env python3
"""
Download sentence transformer model locally
Run this script to download the all-MiniLM-L6-v2 model to ./models/
"""

import os
import sys
from sentence_transformers import SentenceTransformer

def download_model():
    """Download the model to local models directory"""
    model_name = "all-MiniLM-L6-v2"
    models_dir = "./models"
    model_path = os.path.join(models_dir, model_name)
    
    # Create models directory if it doesn't exist
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"Downloading {model_name} to {model_path}...")
    
    try:
        # Download and save the model
        model = SentenceTransformer(model_name)
        model.save(model_path)
        
        print(f"✅ Model successfully downloaded to: {model_path}")
        print(f"Model size: {get_directory_size(model_path):.1f} MB")
        
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        sys.exit(1)

def get_directory_size(path):
    """Get directory size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)

if __name__ == "__main__":
    download_model()