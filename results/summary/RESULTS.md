# Experiment results

Selected on dev: **B**

## Retrieval

| Strategy | Split | Hit@1 | Evidence Hit@3 |
|---|---|---|---|
| A | dev | 6/15 (40.0%) | 10/15 (66.7%) |
| B | dev | 9/15 (60.0%) | 12/15 (80.0%) |
| C | dev | 9/15 (60.0%) | 12/15 (80.0%) |
| A | test | 2/5 (40.0%) | 2/5 (40.0%) |
| B | test | 2/5 (40.0%) | 4/5 (80.0%) |
| C | test | 2/5 (40.0%) | 4/5 (80.0%) |

## Reviewed audit labels

| Strategy | Coherence /2 | Metadata correct | Filter questions passed | Grounding 0/1/2 counts | Grounding /2 | Chunks |
|---|---|---|---|---|---|---|
| A | 1.00 | 15/15 | 1/1 | 1/2/2 | 1.20 | 290 |
| B | 1.80 | 15/15 | 0/1 | 1/0/4 | 1.60 | 196 |
| C | 1.80 | 15/15 | 1/1 | 1/0/4 | 1.60 | 196 |

## Assessment provenance and limits

- Audit labels were drafted with AI assistance. Describe any student verification actually performed.
- AI assessment was not blind to retrieval results.
- B and C share chunks; coherence labels refer to identical chunk content.
- Filter compliance counts questions whose entire top-3 satisfies the requested scope.
- A can return in-scope results without applying a filter.
- Grounding measures retrieved evidence, not generated LLM answer accuracy.
- Test contains only five questions and one filter question; results do not establish general superiority.

Dev run: results\dev\20261113T044849_688540Z
Test run: results/test/20261113T045414_716271Z
Audit files: results/manual/20261113T045414_716271Z
