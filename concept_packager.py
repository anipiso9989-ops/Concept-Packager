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
        Transform the source into compact, actionable Markdown concept packages.
    
        Preservation first; compression second.
        Preserve formulas, definitions, assumptions, conditions, exceptions,
        and boundaries needed to understand, reconstruct, or correctly use
        the source's ideas. Preserve rare exceptions when they affect correctness.
        Do not invent facts, add outside knowledge, or guess how common a case is.
    
        Remove repetition, filler, and redundant examples. Retain examples when
        they carry information that would otherwise be lost.
        Compress wording and merge related ideas without changing their meaning.
        There is no fixed compression percentage.
    
        For each concept, include:
        Primitive: the actionable statement or rule.
        Structure: relationships or reasoning needed to reconstruct it.
        Boundaries: applicable conditions and exceptions, whenever present.
        Use and Relations: include only when useful.
    
        Output only the packaged knowledge in Markdown.
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
