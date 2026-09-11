# Legacy System Modernization for PQC

Welcome to the **Software Development, Maintenance & Operations** group project repository.

## Tools used so far:
* Obsidian to navigate /SDMO/...
* Google Antigravity 2.0
* PlantUML to see the diagtrams in /Documentation/Archive/Diagrams

## Project Overview

The objective of this project is to **develop**, **maintain**, and **modernize** a simulated edge-cloud system by transitioning it to Post-Quantum Cryptography.

### Project's structure so far:
* GEMINI.md --> Instructions for Antigravity 2.0

* /Documentation --> Will hold all the documentation relative to the project
  * /Documentation/Archive --> Word files, old versions of the documentation.
  * /Documentation/Archive/Diagrams --> Contains the UML diagrams.
  * /Documentation/Final --> The documents that may be delivered.

* /SDMO/... is an obsidian notebook:
  * /SDMO/IA Conversation --> Stores logs for IA conversations since we need to document it.
  * /SDMO/Instructions --> PDFs of the introduction lesson for the project
  
* /src --> python code
* /test --> directory for the tests


## Architecture

The system models a common IoT architecture consisting of three primary components:

1. **Legacy Device (IoT Sensor)**
   - Acts as the data source at the edge.
   - Encrypts sensor data locally using a symmetric cipher (AES) and a Pre-Shared Key (PSK).
   - Simulates a low-power device incapable of running modern post-quantum cryptography.

2. **Edge Gateway**
   - Serves as the secure bridge between the legacy edge and the public cloud.
   - Simulate **TLS Termination**: It decrypts incoming legacy data and re-encrypts it for the cloud. 
   - **Modernization Target**: This is the core component we are modernizing to use ML-KEM for its secure key exchange with the Cloud.

3. **Cloud Service**
   - The final destination for the sensor data.
   - Handles the cloud-side of the key exchange and stores/analyzes the incoming encrypted payloads.

## Current Progress:
Implementation of the Legacy System, need group review.

