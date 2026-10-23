# Model evaluation status
Configured V3 model in the captured runtime is gemini-3.8-flash, global, with existing synthetic-tenant access restrictions. Google documents list the model and structured output support:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/control-generated-output

No model training or fine-tuning was performed. This change removes server policy fields from extraction schema and retains original PDF evidence. Routine/complex model routing is not implemented. Current pricing, input limits and regional real-customer approval remain deployment-review dependencies.

The scenario manifest is an evaluation inventory with partial deterministic fixtures, not a completed visual ground-truth dataset. Extraction accuracy, false confirmation rate, false manual-review rate, explanation quality and model cost have not been measured on a representative corpus. Unit success is not a statistical accuracy claim.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
