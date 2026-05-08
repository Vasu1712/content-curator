# Testing Guide

Assumes setup from README.md is complete: Ollama running, Docker services up, Python server started.

---

## Step 0 — Verify Services

Before opening the UI, confirm all four dependencies are reachable.

**FastAPI**
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

**Qdrant**
```bash
curl http://localhost:6333/healthz
# Expected: {"title":"qdrant - vector search engine"}  (or HTTP 200)
```

**Neo4j**
```bash
curl http://localhost:7474
# Expected: HTTP 200 with a JSON body listing available endpoints
```

**Ollama**
```bash
ollama list
# Expected: both llama3 and nomic-embed-text appear in the table
```

If any check fails, stop here — all four must be running for the full test suite to pass.

---

## Test 1 — Direct LLM Path

**Trigger condition:** total content under 1 000 characters, no URLs or files.

**Steps:**

1. Open `http://localhost:8000`
2. In the **Learning Objective** field type:
   ```
   Understand the difference between supervised and unsupervised learning
   ```
   Press Enter or click the arrow button.
3. In the composer textarea paste exactly this text (it is intentionally short):
   ```
   Supervised learning uses labelled data to train a model to predict outputs.
   Unsupervised learning finds patterns in data without labels, using techniques
   like clustering and dimensionality reduction. The key difference is whether
   the training data includes ground-truth outputs.
   ```
4. Click the send button.

**Expected result:**
- The workspace loads with the objective card, a content preview, a curated bundle, and a dynamic challenge.
- The strategy badge in the top-right reads **Direct LLM** (amber).
- No Qdrant or Neo4j calls are made (nothing to verify externally, but generation is fast — typically under 30 s).

**If it fails:**
- A toast with "LLM failed to produce a valid response" means llama3 returned unparseable output — retry once; the model is non-deterministic.
- A blank workspace with no error usually means the server crashed; check the uvicorn terminal.

---

## Test 2 — Qdrant RAG Path

**Trigger condition:** single source, total content ≥ 1 000 characters.

**Steps:**

1. Click **New session**.
2. Set the learning objective:
   ```
   Understand how transformer attention mechanisms work
   ```
3. Click the **link icon** in the composer bar, paste this URL, and click **Add Source**:
   ```
   https://en.wikipedia.org/wiki/Attention_(machine_learning)
   ```
4. Leave the text area empty and attach no files.
5. Click the send button.

**Expected result:**
- The strategy badge reads **Vector RAG** (violet).
- The curated bundle reflects concepts from the Wikipedia article (query-key-value, scaled dot-product, multi-head attention).
- The dynamic challenge asks the learner to apply or explain a specific mechanism from that article.

**What happens internally:**
- The URL is fetched and stripped to plain text (~several thousand characters).
- Content is chunked (500 chars, 50 overlap), embedded with `nomic-embed-text`, inserted into a per-session Qdrant collection, and the top-4 cosine-similar chunks are retrieved against the objective.
- The collection is deleted after retrieval.

**If it fails:**
- "No relevant context found" means Qdrant is unreachable or the URL returned empty content. Confirm `curl http://localhost:6333/healthz` passes and the URL is accessible from your machine.
- A 502 error means llama3 returned unparseable JSON — retry.

---

## Test 3 — Neo4j RAG Path

**Trigger condition:** two or more sources, total content ≥ 1 000 characters.

**Prepare a test file** — save this as `ml-glossary.txt` on your desktop:

```
Overfitting occurs when a model learns the training data too well, including
its noise, and performs poorly on unseen data. It is characterised by low
training error and high validation error.

Regularisation techniques such as L1 (Lasso) and L2 (Ridge) add a penalty
term to the loss function to discourage large weights and reduce overfitting.

Cross-validation splits the dataset into k folds, trains on k-1 folds, and
validates on the remaining fold, cycling through all folds to get a robust
estimate of generalisation performance.

Dropout is a regularisation method for neural networks that randomly sets a
fraction of neuron activations to zero during training, preventing
co-adaptation of neurons.
```

**Steps:**

1. Click **New session**.
2. Set the learning objective:
   ```
   Understand techniques to prevent overfitting in machine learning models
   ```
3. Add the URL source (link icon):
   ```
   https://en.wikipedia.org/wiki/Regularization_(mathematics)
   ```
4. Attach `ml-glossary.txt` via the paperclip icon.
5. Click send.

**Expected result:**
- The strategy badge reads **Graph RAG** (green).
- The curated bundle draws on both sources — the Wikipedia article and the uploaded file.
- The dynamic challenge references at least one concrete technique (L1/L2, dropout, cross-validation).

**What happens internally:**
- Both sources are chunked and embedded. Chunks are written as `ContentChunk` nodes in Neo4j with a per-session vector index.
- The top-5 most relevant chunks are retrieved. All `ContentChunk` nodes for this session are deleted after retrieval via a `DETACH DELETE` Cypher query.

**If it fails:**
- Check Neo4j is running: `curl http://localhost:7474` should return HTTP 200.
- "No relevant context found" on a multi-source request usually means both sources returned empty content — confirm the URL is reachable and the file was non-empty.

---

## Test 4 — Evaluation: Passing Answer

Run after any successful curation (Tests 1–3 all produce a challenge).

**Steps:**

1. Read the **Dynamic Challenge** card carefully.
2. Read the **Required Output** box below it — this is the scoring rubric.
3. Write a thorough answer that explicitly addresses each point in the required output. Example for Test 1's supervised/unsupervised challenge:
   ```
   Supervised learning requires labelled training data where each example has
   a known output. The model learns a mapping from inputs to outputs and can
   make predictions on new data. Examples include classification and regression.

   Unsupervised learning works with unlabelled data and discovers hidden
   structure. Clustering (e.g. k-means) groups similar examples; dimensionality
   reduction (e.g. PCA) compresses features. There are no ground-truth labels
   to guide training.

   The core difference is the presence or absence of labels: supervised learning
   optimises against known targets, unsupervised learning does not.
   ```
4. Click **Submit Answer**.

**Expected result:**
- Score **≥ 0.7**, verdict badge shows **✓ Passed** (green).
- Feedback identifies what was good and, if applicable, any minor gaps.
- Score bar animates to the correct percentage.

---

## Test 5 — Evaluation: Failing Answer

**Steps:**

1. After a curation, type a deliberately shallow answer in the answer field:
   ```
   They are different types of machine learning.
   ```
2. Click **Submit Answer**.

**Expected result:**
- Score **< 0.7**, verdict badge shows **✗ Keep going** (red).
- Feedback names the missing criteria and suggests how to improve.

**If both Tests 4 and 5 return the same score (~0.8):** the evaluator is exhibiting score inflation. This is a known llama3 behaviour; see `evaluation.md` for context.

---

## Test 6 — Improved Solution

**Steps:**

1. Complete any evaluation (passing or failing).
2. Wait **5 seconds** — the **Improved Solution** button appears at the bottom-right of the evaluation card.
3. Click it. The button text changes to **Generating…** and disables.

**Expected result:**
- An **Improved Solution** card slides in below the evaluation card.
- The top section shows a complete rewritten answer.
- Below it, 2–4 improvement bullets appear, each with a label (what changed) and a reason (why it matters), styled with a purple left border.

**If it fails:**
- A "Could not generate improved solution" toast means `improve_answer` caught an exception. Check the uvicorn terminal for the traceback — most commonly a JSON parse failure from llama3 output containing unescaped control characters.

---

## Test 7 — New Session Reset

**Steps:**

1. While on the workspace screen (after any curation), click **← New session** in the top-left.

**Expected result:**
- The screen returns to the input view.
- The objective field is empty.
- The composer textarea, file button, URL button, and send button are all **disabled**.
- The composer hint text reappears: "Set your objective first, then add source content."
- All workspace cards (objective, preview, bundle, challenge, evaluation, improved solution) are cleared.

**If the composer buttons remain enabled** after returning to the input screen, the reset logic in `btnNewSession` has a bug.

---

## Quick Reference — Strategy Routing

| Sources provided | Content size | Strategy | Badge |
|---|---|---|---|
| Text only | < 1 000 chars | Direct LLM | Amber — **Direct LLM** |
| 1 URL (no file/text) | ≥ 1 000 chars | Qdrant RAG | Violet — **Vector RAG** |
| URL + file, or 2+ URLs | ≥ 1 000 chars | Neo4j RAG | Green — **Graph RAG** |
| Text only | ≥ 1 000 chars | Qdrant RAG | Violet — **Vector RAG** |

The strategy badge is the single fastest way to confirm the correct path ran.
