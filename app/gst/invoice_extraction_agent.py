"""Restricted document reader: no database tools, web tools or mutation authority."""
import time
from google import genai
from google.genai import types
from app.services.model_access import extraction_model_location
from app.services.performance import measure


class InvoiceExtractionAgent:
    """A stateless request scoped to one authorized business and one original.

    Storage/membership checks stay in the API/worker. The model receives only this
    original and the selected GSTIN context. It cannot fetch other invoices,
    execute document instructions, update records or make review decisions.
    """
    def __init__(self, settings, client_id):
        self.settings=settings
        location=extraction_model_location(client_id,settings)
        self.client=genai.Client(vertexai=True,project=settings.gcp_project_id,location=location,
            http_options=types.HttpOptions(timeout=settings.external_timeout_seconds*1000))

    def read(self, contents, schema):
        for attempt in range(2):
            try:
                with measure('vertex_document_read'):
                    return self.client.models.generate_content(model=self.settings.gemini_model,contents=contents,
                        config=types.GenerateContentConfig(temperature=0,response_mime_type='application/json',response_schema=schema,
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
            except Exception as exc:
                code=getattr(exc,'code',None) or getattr(exc,'status_code',None)
                transient=(code in {429,500,502,503,504} or isinstance(exc,(TimeoutError,ConnectionError))
                           or 'timeout' in type(exc).__name__.lower())
                if attempt or not transient:
                    raise
                time.sleep(.5)
