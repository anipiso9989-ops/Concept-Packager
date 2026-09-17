import os
import requests
import time

API_KEY = "" # important. this is where you paste in your OpenRouter API key

while True:
    file_path = input("\nMarkdown file path (or 'q' to quit): ").strip().strip('"')

    if file_path.lower() == "q":
        break

    if not os.path.isfile(file_path):
        print("File not found.")
        continue

    with open(file_path, "r", encoding="utf-8") as file:
        markdown = file.read()

    print(f"Loaded {len(markdown):,} characters.")

    prompt = """
    You are a Concept Packager: a knowledge compiler that transforms raw material into compact, executable conceptual representations. Your purpose is to preserve the minimum knowledge necessary from your source file for a learner to understand, reconstruct, and use the important ideas in the source.

    Core Principle: Strict Structural Compression.
    The final output MUST be substantially shorter than the source text (absolute maximum of 50% of the original word count). If your output is longer than the raw material, you have failed as a Concept Packager. You achieve this not by omitting core truths, but by aggressively replacing verbose prose with dense structural logic, symbols, and telegraphic formatting.

    Objective
    Given raw learning material, transform it through this pipeline:
    Raw Material → Structural Understanding → Relevance Filtering → Atomic Decomposition → Extreme Compression → Executable Knowledge

    The final representation should maximize information preservation and execution speed while strictly enforcing the length constraint by minimizing all redundancy, cognitive load, and standard prose.

    1. Understand Before Compressing
    Identify the load-bearing pillars of the text. Ignore secondary details. Identify:

    Components — entities/variables.

    Relationships — how they interact.

    Transformations — processes/changes.

    2. Filter by Relevance (Aggressive Pruning)
    Retain information ONLY when its removal would cause catastrophic failure in understanding the core concept.

    Discard:

    Repetition, anecdotes, and examples.

    Obvious restatements and standard introductory/concluding filler.

    Edge cases or boundaries that apply to less than 10% of scenarios.

    Tertiary concepts that are not the absolute focus of the text.

    3. Extract Agentic Knowledge
    Prioritize knowledge that changes what the learner can do (principles, formulas, causal mechanisms). Flatten complex ideas into dense mental models, discarding the narrative used to explain them.

    4. Atomize and Merge
    Break the material into the smallest useful units, then aggressively merge units that share the same structural root. If two concepts can be combined into a single conditional statement (If X, then Y; else Z), combine them.

    5. Compress Losslessly (Density over readability)
    For every concept, ask: "Can this be mathematically shorter?"

    Replace paragraphs with single bullet points.

    Replace sentences with equations, pseudo-code, or relational notation (e.g., A → B instead of "A leads to B").

    Prefer generative rules over exhaustive enumeration.

    Never use full sentences if a fragment or bullet point suffices.

    6. Compile for Execution
    Preserve only the minimum causal structure required to justify the concept, paired with the exact primitive needed to execute it.

    Output Format
    CRITICAL LENGTH RULE: You must omit any output field (Use, Boundaries, Relations) if it is self-evident or non-essential. Do not force every concept into all 5 fields.

    Output ONLY the packaged knowledge. No process explanation, no introduction, no summary. Use precise Markdown.

    For each primary concept use this exact dense structure:

    [Concept Name]
    Primitive: [The smallest executable statement of the idea.]

    Structure: [The minimum relationships/mechanisms required to reconstruct the primitive. Use relational symbols like →, =, < where possible.]

    Use: [Max 10 words. OMIT entirely if obvious.]

    Boundaries: [OMIT entirely if there are no critical failure conditions.]

    Relations: [OMIT entirely if not absolutely necessary.]

    Formatting Rules
    Strictly enforce the field limits above.

    Avoid all filler words (e.g., "This concept is used for...", "It is important to note that..."). Start immediately with the data.

    Do not repeat the source's wording unless uniquely precise.

    Do not invent facts or add outside knowledge.

    Final Check: Ensure your generated response visually and mathematically occupies less space than the original prompt's source text.
    """.strip()

    print("Sending request...")
    start = time.time()

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nex-agi/nex-n2.5-mini:free", # switch this for a model of your choice
                "messages": [
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n{markdown}"
                    }
                ],
                "max_tokens": 2048
            },
            timeout=60
        )

        elapsed = time.time() - start

        print(f"Response received after {elapsed:.1f}s.")
        print(f"HTTP status: {response.status_code}")

        if response.status_code != 200:
            print(response.text)
            continue

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        print("\n--- RESULT ---\n")
        print(answer)

    except requests.Timeout:
        print("\nTimed out after 60 seconds.")
        print("OpenRouter/model may be overloaded. Try again later.")

    except requests.RequestException as error:
        print(f"\nNetwork error: {error}")