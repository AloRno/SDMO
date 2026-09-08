# Legacy System Modernization for PQC

Welcome to the **Software Development, Maintenance & Operations** group project repository.

## Tools used so far:
* Obsidian to navigate /SDMO/...
* Google Antigravity 2.0

## Project Overview

The objective of this project is to develop, maintain, and modernize a simulated edge-cloud system by transitioning it to Post-Quantum Cryptography (specifically, the ML-KEM/Kyber key exchange algorithm). This is an AI-assisted development effort where we critically evaluate, test, and integrate LLM-generated artifacts.

### Project's structure so far:
* GEMINI.md --> Instructions for Antigravity 2.0
* /Diagrams --> UML diagrams.
* /SDMO/... is an obsidian notebook:
  * /SDMO/IA Conversation --> Stores logs for IA conversations since we need to document it.
  * /SDMO/Instructions --> PDFs of the introduction lesson for the project
  * /SDMO/Notes --> Hand-taken notes

## Architecture

The system models a common IoT architecture consisting of three primary components:

1. **Legacy Device (IoT Sensor)**
   - Acts as the data source at the edge.
   - Encrypts sensor data locally using a symmetric cipher (AES/ChaCha20) and a Pre-Shared Key (PSK).
   - Simulates a low-power device incapable of running modern post-quantum cryptography.

2. **Edge Gateway**
   - Serves as the secure bridge between the legacy edge and the public cloud.
   - Performs **TLS Termination**: It decrypts incoming legacy data and re-encrypts it for the cloud.
   - **Modernization Target**: This is the core component we are modernizing to use ML-KEM for its secure key exchange with the Cloud.

3. **Cloud Service**
   - The final destination for the sensor data.
   - Handles the cloud-side of the key exchange and stores/analyzes the incoming encrypted payloads.

## Current Progress: Phase 0 (Baseline)

We are currently in **Phase 0**, which focuses on understanding the architecture and building the initial, vulnerable baseline system.

### Achievements so far:
*   **Separation of Responsibilities**: Mapped out exactly how data flows from the sensor to the cloud.
*   **Diagramming**: Designed the system flow using PlantUML. You can find our diagrams in the `SDMO/Diagrams/` directory:
    *   `use_case_diagram.puml`: High-level responsibilities.
    *   `sequence_diagram_phase0.puml` (and `Sequence_Diagram_Second_Proposition.puml`): The step-by-step cryptographic handshake and data transmission sequence.
    *   `Class_Diagram_Phase0.puml`: The object-oriented blueprint for our Python implementation.

### Next Steps
Our next goal is to implement the Phase 0 baseline system in Python, keeping the code as simple and functional as possible. Once the baseline is operational, we will move to **Phase 2**, where we will integrate ML-KEM into the Gateway-Cloud link.
