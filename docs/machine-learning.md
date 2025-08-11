# Machine Learning Pipeline

This document outlines the architecture and implementation of the machine learning pipeline for intelligent transaction categorization, based on the current state of the codebase.

## 1. ML Pipeline Overview

The ML pipeline is designed for asynchronous processing of transaction categorization tasks using a Celery worker.

![ML Pipeline Diagram](./images/ml-pipeline.png)
*Figure 3: Machine Learning Pipeline*

### Pipeline Stages

1.  **Task Trigger:** When a new transaction is created, a Celery task is created to categorize it.
2.  **ML Worker:** A dedicated Celery worker picks up the task and uses a pre-trained Sentence Transformer model to generate an embedding for the transaction description.
3.  **Classification:** The transaction embedding is compared to pre-defined category embeddings to find the best match.
4.  **Database Update:** The categorized transaction is updated in the database.

## 2. Model Details

*   **Model:** `all-MiniLM-L6-v2` (Sentence Transformer)
*   **Location:** The model is stored in the `ml-worker/models` directory.

## 3. ML Worker

*   The `ml-worker` service is a Celery worker that is responsible for running the ML tasks.
*   It uses the `ml_classification_service.py` to perform the transaction categorization.

## 4. ONNX and Optimization

*   The `onnx_converter.py` and `optimized_inference_engine.py` files suggest that the project is set up to use ONNX for optimized model inference, which can significantly improve performance.