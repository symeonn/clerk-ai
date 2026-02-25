# Second Brain

This repository contains the implementation of a "Second Brain" system based on a local Markdown vault.

## Stages

*   **Stage 0: Repo & Rules** - Repository structure, rules, schemas, and vault invariants.
*   **Stage 1: Vault Structure & Project Model** - Vault directory structure and project model rules.
*   **Stage 2: Cognitive Engine (Isolated)** - Pure stateless reasoning component for classification, summarization, and routing.

## Usage

1.  Populate `.env` with your secrets.
2.  Configure `config.yaml` as needed.
3.  Run the service using Docker Compose:

    ```bash
    docker-compose up
    ```

    To run in test mode:

    ```bash
    docker-compose run second-brain-core --test
    ```

### Deploy to QNAP

1.  Build and copy image to QNAP (use in module folder):

    ```bash
    ./QNAP/deploy-to-qnap.sh <image-name>
    ```

2.  Run on QNAP using:

    ```bash
    docker-compose -f QNAP/docker-compose-qnap.yml up
    ```
