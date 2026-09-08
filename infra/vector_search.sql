-- Run after Terraform creates the table. VECTOR_SEARCH falls back to brute force if no index exists.
CREATE VECTOR INDEX IF NOT EXISTS document_embeddings_vector_idx
ON `PROJECT_ID.finance_analytics.document_embeddings`(embedding)
OPTIONS(index_type='IVF', distance_type='COSINE', ivf_options='{"num_lists":100}');
