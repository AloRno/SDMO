# SDMO: Legacy System Modernization for PQC


This repository contains a simulated edge-cloud telemetry pipeline that has been modernized to withstand quantum computing threats. We successfully migrated the infrastructure's transport encryption from a classical Diffie-Hellman handshake to a **Hybrid DH + ML-KEM768** key encapsulation mechanism, while maintaining backward compatibility with a simulated legacy IoT sensor.

---

## Architecture Overview

The system models a common IoT architecture consisting of three primary components:

1. **Legacy Device (IoT Sensor)**
   - Acts as the data source at the edge.
   - Encrypts sensor data locally using a symmetric cipher (AES-CBC) and a Pre-Shared Key (PSK).
   - Simulates a low-power device incapable of running modern post-quantum cryptography.

2. **Edge Gateway**
   - Serves as the secure bridge between the legacy edge and the public cloud.
   - Simulates **TLS Termination**: It decrypts incoming legacy data and re-encrypts it for the cloud.
   - **Modernization Target**: Secures its connection to the cloud using a Hybrid DH + ML-KEM key exchange and AES-256-GCM authenticated encryption.

3. **Cloud Service**
   - The final destination for the sensor data.
   - Handles the cloud-side of the Hybrid key exchange.
   - Validates incoming payloads for transit corruption or hardware malfunctions.
   - Exposes clean telemetry metrics to a centralized Prometheus monitoring system.

---

## Quickstart

The entire pipeline (including the Prometheus monitoring database) is containerized for seamless deployment.

### Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose installed.

### Running the System
To start the pipeline in the background, open your terminal in the root directory of this project and run:
```bash
sudo docker compose up --build -d
```
The system will automatically negotiate the post-quantum session and begin silently streaming telemetry data.

To shut the system down:
```bash
sudo docker compose down
```
---

## Monitoring & Telemetry

Once the containers are running, you can monitor the live telemetry data using the built-in **Prometheus Time-Series Database**.

1. Open your web browser and navigate to: `http://localhost:9090`
2. In the query bar, you can search for the following custom metrics:
   - `sdmo_temperature_celsius` (Gauge)
   - `sdmo_packets_total` (Counter)
   - `sdmo_errors_total` (Counter)
3. Select the **Graph** tab and choose a rolling window (e.g., *Last 5 minutes*) to watch the real-time data flow.

*Note: You can also extract this data programmatically by querying the Prometheus HTTP API (`http://localhost:9090/api/v1/query`).*

---

## Extracting Gateway Logs

Because the pipeline runs inside isolated Docker containers to guarantee thread stability, runtime files (like logs) are kept securely inside the container's virtual filesystem.

To extract the Edge Gateway's live error log to your host machine, run:
```bash
sudo docker cp sdmo-sdmo-app-1:/app/src/Output_Components/gateway/gateway_error.log ./gateway_error.log
```

---

## Running the Test Suite

If you want to run the automated test suite locally (which validates the hybrid cryptography, baseline metrics, and failure handling), you will need Python 3.12.

1. Activate your virtual environment and install dependencies:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the `pytest` suite (ensuring the `src/` directory is in your Python path):
   ```bash
   export PYTHONPATH=src && pytest tests/
   ```

---

## Repository Structure

* `/src` — The core Python source code for the pipeline.
* `/tests` — Automated test suite for regression and cryptography testing.
* `/Documentation/Fina` — All formal project reports, delivery documents, and architectural diagrams.
* `/SDMO` — Obsidian notebook containing project instructions and AI logs.

## Final Reports
[Main_Project_Documentation](Documentation/Final/Main_Documentation.pdf)
[Report_ML_KEM](Documentation/Final/Project_Report.pdf)
