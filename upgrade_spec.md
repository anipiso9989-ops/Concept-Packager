***
# Concept Packager — Upgrade Specification

Concept Packager is a knowledge-compilation system that transforms raw learning material into compact, executable representations while prioritizing information preservation and reconstructability over compression alone.

The upgraded system consists of three integrated components: **Structural Concept Compilation**, **Reconstructability Evaluation**, and **Adaptive Compression**.

The complete pipeline is:

```text
Raw Source
    ↓
Structural Extraction
    ↓
Atomic Knowledge Representation
    ↓
Goal-Conditioned Compilation
    ↓
Concept Package
    ↓
Reconstructability Evaluation
```

## 1. Structural Concept Compiler

Concept Packager should not directly transform source material into compressed Markdown. It should first construct an intermediate structural representation (IR) of the knowledge contained in the source.

The pipeline becomes:

```text
Source
    ↓
Extract concepts
    ↓
Atomize concepts
    ↓
Identify relationships
    ↓
Identify constraints and boundaries
    ↓
Construct knowledge structure
    ↓
Compile Concept Package
```

### Atomic Concepts

The system decomposes the source into the smallest standalone concepts that remain independently interpretable.

Each concept should contain knowledge that is not already represented by another concept.

For example:

```json
{
  "id": "newtons_second_law",
  "name": "Newton's Second Law",
  "type": "principle",
  "content": "Net force determines the acceleration of an object relative to its mass."
}
```

These concepts form the basic units from which larger knowledge structures are constructed.

### Relationships

The compiler then determines how those concepts relate.

Relationships should be explicitly typed rather than represented only through prose. Possible relationships include:

```text
A → B     A causes or produces B
A requires B
A is-part-of B
A generalizes B
A contrasts-with B
A constrains B
A × B     A and B interact
A - B     A and B operate jointly
```

For example:

```text
Net Force → Acceleration
Mass constrains Acceleration
Newton's Second Law requires Net Force
Newton's Second Law requires Mass
Newton's Second Law requires Acceleration
```

### Constraints and Boundaries

The representation should preserve not only what a principle says, but also the conditions under which it remains valid.

For example:

```json
{
  "concept": "newtons_second_law",
  "constraints": [
    "Requires an inertial reference frame",
    "F represents net external force",
    "Classical formulation assumes constant mass"
  ]
}
```

This prevents compression from turning conditional knowledge into misleading universal rules.

### Intermediate Knowledge Representation

The result of structural extraction should be a machine-readable representation separate from the final Markdown.

For example:

```text
Newton's Second Law
│
├── Components
│   ├── Net Force
│   ├── Mass
│   └── Acceleration
│
├── Relations
│   ├── Net Force → Acceleration
│   └── Mass constrains Acceleration
│
├── Constraints
│   ├── Inertial reference frame
│   └── Net external force
│
└── Compressed Representation
    └── F = ma
```

Concept Packager operates more like a compiler:

```text
Source Material = source code

Structural Knowledge Representation = intermediate representation

Concept Package = compiled representation
```

Markdown is simply one human-readable output format generated from this underlying structure.

---

## 2. Reconstructability Evaluator

Concept Packager should empirically test whether its compression preserved the knowledge required to reconstruct and use the original material.

The evaluation pipeline is:

```text
Original Source
      ↓
Concept Packager
      ↓
Concept Package
      ↓
Isolated Reconstruction
      ↓
Reconstructed Knowledge
      ↓
Compare against Original Structure
```

The reconstruction stage receives **only the Concept Package**. It does not receive the original source.

Its task is to reconstruct the important concepts, relationships, constraints, and procedures represented by the original material.

### Evaluation Dimensions

The evaluator should measure several independent properties.

**Compression Ratio**

Measures how much smaller the package is than its source.

```text
Compression Ratio =
Original Token Count / Package Token Count
```

For example:

```text
Original: 8,400 tokens
Package:  1,000 tokens

Compression Ratio: 8.4×
```

**Concept Preservation**

Measures how many important concepts remain directly represented or reconstructable.

```text
Preserved Concepts / Required Concepts
```

**Relationship Preservation**

Measures whether the important causal, logical, prerequisite, and structural relationships remain recoverable.

A package that remembers every individual concept but destroys their relationships should therefore score poorly.

**Constraint Preservation**

Measures whether important boundaries, assumptions, exceptions, and failure conditions survive compression.

**Reconstruction Performance**

Measures how accurately the original knowledge structure can be recovered using only the compiled package.

The resulting report could look like:

```text
PACKAGE EVALUATION

Source tokens:             8,420
Package tokens:            1,003
Compression ratio:         8.39×

Concept preservation:      96%
Relationship preservation: 91%
Constraint preservation:   94%
Reconstruction score:      93%
```

### Compression Frontier

The evaluator can generate packages at different compression levels and determine when additional compression begins destroying reconstructability.

For example:

```text
Compression    Reconstruction
2×             99%
4×             98%
6×             96%
8×             94%
10×            86%
12×            69%
```

The objective is therefore not:

```text
maximize compression
```

but approximately:

```text
maximize compression
subject to:
    preservation >= required threshold
    reconstructability >= required threshold
```

This provides a concrete method for finding the smallest representation that still preserves the functional knowledge contained in the source.

### Baseline Comparison

The benchmark should also compare Concept Packager against simpler compression methods.

For example:

```text
Method                 Tokens    Reconstruction
------------------------------------------------
Original Source         8,400        100%
Standard Summary          420         61%
Detailed LLM Notes        710         79%
Concept Package           530         94%
```

This allows the project to test whether structural concept packaging actually preserves more usable knowledge per token than ordinary summarization.

---

## 3. Adaptive Compression

Concept Packager should not assume that one universally optimal representation of a source exists.

Instead, compilation should be conditioned on the user's intended objective.

The interface could expose this directly:

```bash
concept-packager physics.pdf --goal solve-problems

concept-packager physics.pdf --goal teach

concept-packager physics.pdf --goal retain

concept-packager physics.pdf --goal reference
```

The Structural Concept Compiler still extracts the same underlying knowledge structure.

The goal determines **which parts of that structure receive priority during compilation**.

### `solve-problems`

Optimizes the representation for execution.

Prioritize:

```text
procedures
equations
constraints
decision rules
inputs/outputs
failure conditions
edge cases
```

Explanatory material can be compressed aggressively when it does not contribute to successful execution.

### `teach`

Optimizes the representation for communicating understanding.

Prioritize:

```text
definitions
prerequisites
causal relationships
conceptual intuitions
examples
contrasts
common misconceptions
```

The package may therefore be larger because explanations that would be unnecessary during execution become important for teaching.

### `retain`

Optimizes for long-term reconstruction.

Prioritize:

```text
conceptual skeleton
retrieval cues
critical relationships
prerequisite chains
memorable anchors
strategic redundancy
```

Redundancy may intentionally remain when removing it would make later reconstruction fragile.

### `reference`

Optimizes for fast retrieval.

Prioritize:

```text
definitions
formulas
properties
tables
constraints
lookup information
clear categorization
```

Narrative explanation is minimized unless required to interpret the reference information correctly.

### Goal-Conditioned Compilation

This means a single structural representation can produce multiple valid packages.

```text
                         ┌─→ Problem-Solving Package
                         │
Source → Knowledge IR ───┼─→ Teaching Package
                         │
                         ├─→ Retention Package
                         │
                         └─→ Reference Package
```

The underlying knowledge has not changed.

What changes is the definition of **relevant information**.

The compiler therefore attempts to find the smallest representation that preserves the structure required for a particular objective rather than simply finding the shortest possible representation.

---

## Integrated Architecture

Together, the three upgrades create one system rather than three independent features.

```text
                         CONCEPT PACKAGER

Raw Material
     │
     ▼
┌─────────────────────────────────┐
│  Structural Concept Compiler    │
│                                 │
│  Extract concepts               │
│  → atomize                      │
│  → identify relationships       │
│  → identify constraints         │
│  → construct Knowledge IR       │
└───────────────┬─────────────────┘
                │
                ▼
        Knowledge Structure
                │
                │ + User Goal
                ▼
┌─────────────────────────────────┐
│      Adaptive Compression       │
│                                 │
│  Determine relevance            │
│  → preserve required structure  │
│  → remove unnecessary material  │
│  → retain strategic redundancy  │
│  → compile representation       │
└───────────────┬─────────────────┘
                │
                ▼
          Concept Package
                │
                ▼
┌─────────────────────────────────┐
│   Reconstructability Evaluator  │
│                                 │
│  Attempt reconstruction         │
│  → compare concepts             │
│  → compare relationships        │
│  → compare constraints          │
│  → measure compression          │
│  → calculate package quality    │
└───────────────┬─────────────────┘
                │
                ▼
        Evaluation Report
```

The upgraded Concept Packager is therefore a **goal-conditioned knowledge compiler**: it extracts the structural knowledge contained in raw material, represents that knowledge as atomic concepts and explicit relationships, compiles the structure into a minimal representation optimized for a particular use case, and empirically tests whether the resulting package remains capable of reconstructing the important knowledge contained in the original source.