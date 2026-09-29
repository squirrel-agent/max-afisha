# Architecture

```text
External event pages
      ↓
parser-service (Playwright/HTTP parsing)
      ↓
FastAPI admin ingestion
      ↓
PostgreSQL 16 + pgvector
      ↓
Event embeddings + user 5-answer semantic profile
      ↓
Hard constraints → semantic/final relevance gates → ranker
      ↓                                  ↘ no relevant
personalized podium                explicit no-match
      ↓                                  ↓
React mini-app ← MAX Bridge       baseline city feed
```

## Separation of responsibilities

- `parser-service`: acquisition/normalization only; it does not make user recommendations.
- `backend`: source upsert, embeddings, preference profile, filters, ranking, MAX initData verification, audit/run ids.
- `postgres`: persistent events/users/interactions and pgvector embeddings.
- `frontend`: five-question onboarding, personalized result, explicit empty-result state, fallback city feed, visible source provenance.

The fallback feed is deliberately separate from ML recommendations. A low-confidence nearest neighbour is never used merely to fill UI space.
