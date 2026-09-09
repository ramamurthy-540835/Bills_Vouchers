from google.cloud import bigquery

from ..config import get_settings


class EmbeddingService:
    def __init__(self, repo):
        self.repo = repo

    def embed(self, text, task):
        from google import genai
        from google.genai.types import EmbedContentConfig

        s = get_settings()
        c = (
            genai.Client(api_key=s.gemini_api_key)
            if s.gemini_api_key
            else genai.Client(vertexai=True, project=s.gcp_project_id, location=s.gcp_region)
        )
        r = c.models.embed_content(
            model=s.embedding_model,
            contents=[text[:12000]],
            config=EmbedContentConfig(task_type=task, output_dimensionality=s.embedding_dimensions),
        )
        if not r.embeddings or r.embeddings[0].values is None:
            raise RuntimeError("Embedding service returned no vector.")
        return list(r.embeddings[0].values)

    def index(self, document, extraction):
        text = " | ".join(
            str(x or "")
            for x in [extraction.vendor_name, extraction.invoice_number, extraction.gstin, extraction.ocr_text]
        )
        row = {
            "id": document.id,
            "document_id": document.id,
            "content": text,
            "embedding": self.embed(text, "RETRIEVAL_DOCUMENT"),
            "document_type": document.document_type.value,
            "status": document.status.value,
            "vendor_name": extraction.vendor_name,
            "invoice_number": extraction.invoice_number,
            "gstin": extraction.gstin,
            "total_amount": str(extraction.total_amount) if extraction.total_amount is not None else None,
            "gcs_uri": document.gcs_uri,
            "created_at": str(document.uploaded_at),
        }
        self.repo.bq.insert("document_embeddings", row, document.id)

    def search(self, text, top_k=10):
        vector = self.embed(text, "RETRIEVAL_QUERY")
        params = [
            bigquery.ArrayQueryParameter("embedding", "FLOAT64", vector),
            bigquery.ScalarQueryParameter("top_k", "INT64", min(max(top_k, 1), 50)),
        ]
        table = self.repo.bq.table("document_embeddings")
        sql = (
            "SELECT base.document_id,base.content,base.document_type,base.vendor_name,base.invoice_number,base.gstin,base.total_amount,base.gcs_uri,distance FROM VECTOR_SEARCH(TABLE `"
            + table
            + "`, 'embedding', query_value=>@embedding, top_k=>@top_k, distance_type=>'COSINE', options=>'{\"use_brute_force\":true}') ORDER BY distance"
        )
        return [dict(r.items()) for r in self.repo.bq.query(sql, params)]
