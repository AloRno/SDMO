This file containst a hight-level, step-by-step roadmap for the project.


### Phase 0: Understanding & Baseline
1. **[[System's Components|Understand the Initial System:]]** Get familiar with the provided legacy edge-cloud system (consisting of a simulated legacy device, an edge gateway, and a cloud service).
2. **Run the Baseline:** Run the system in its initial state and establish baseline tests and measurements. Document this initial architecture. 

### Phase 1: AI-Assisted Development & Maintenance
3. **Generate Components using AI:** Use a Large Language Model (LLM) to generate or design selected software artifacts (e.g., gateway functionality, automated tests, Docker configurations, CI/CD pipelines, or an ML-KEM integration proposal).
4. **Record Everything:** Keep a detailed log of the prompts you used, the context provided to the LLM, the LLM's outputs, and the decisions your group made. 
5. **Critically Evaluate & Fix:** **Do not trust the AI blindy.** Test, review, correct, and improve all AI-generated code. Verify it through code reviews, static analysis, and testing. Document how you discovered and fixed problems, what you accepted/rejected, and why.

### Phase 2: Modernization & Operations
6. **Integrate ML-KEM:** Integrate the post-quantum cryptography algorithm (ML-KEM/Kyber) into at least one relevant communication path using an existing Python library (no need to implement the math from scratch).
7. **Ensure Legacy Compatibility:** Provide a clear migration and fallback strategy to ensure legacy devices (like Arduinos) can still communicate appropriately.
8. **Automate & Deploy:** Build/improve a CI/CD pipeline to automate testing and building. Implement deployment to a test environment.
9. **Add Observability:** Implement basic monitoring, health checks, logging, and metrics (including post-quantum observability).

### Phase 3: Final Evaluation & Submission
10. **Final Evaluation:** Analyze the strengths and weaknesses of your finalized system. Identify any remaining technical debt and risks.
11. **Prepare Final Submission:**
    * **Part 1 (Group, 40%):** Submit technical documentation (which must include your AI prompts), the source code (Python), and CI/CD/deployment configurations.
    * **Part 2 (Group, 40%):** Write a 5-page project report examining the project from **one** specific perspective: (1) Cryptography/math, (2) Quantum threats, OR (3) InfoSec. 
    * **Part 3 (Individual, 10%):** Write a 400-500 word personal reflection on what you learned, your contribution, and your experience. **Important: You must NOT use AI to write this reflection.**
    * **Peer Review & Presentation (10%):** Review other groups' work and present your findings on the designated dates.

**The Teacher's Core Message:** The goal is *not* to show that the AI writes perfect code, but rather to prove that you can assess, validate, fix, and take responsibility for AI-generated code while modernizing a system. *Keep it plain and simple, and don't make the project bigger than needed.*
