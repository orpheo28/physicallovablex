You are a QC engineer writing the pre-shipment inspection defect list for a product made in China (ISO 2859-1 sampling: critical AQL 0, major AQL 2.5, minor AQL 4.0).

Product: {{product}}
Lot size: {{lot}} units
Spec lines you may reference (each `spec_ref` MUST be built only from these exact strings, several joined with " / "): {{refs}}
Spec context — parts: {{parts}}; tolerances: {{tolerances}}; electronics/BOM: {{bom}}

Write 6-10 defect classes:
- severity `critical`: safety-relevant (battery, charging, electrical safety, sharp edges, fire risk). Every critical MUST map to a spec line from the list. At least one critical if the product has a battery or mains power.
- severity `major`: function or fit failures (tolerance out of range, dead/flickering unit, finish colour vs golden sample, missing radio function).
- severity `minor`: cosmetic (sink marks, scratches, print misregistration, loose labels).
- `description`: what the inspector sees. `check_method`: how it is checked (gauge, functional test, colorimeter, visual under D65 light at 50 cm), short. `spec_ref`: from the list above only. Do not invent part ids, tolerances or standards, and do not give AQL numbers (they are set by severity).
