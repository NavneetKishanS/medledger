
import os
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "patient_report_template.html")

env = Environment(loader=FileSystemLoader(os.path.dirname(TEMPLATE_DIR)))


def render_patient_pdf(context: dict) -> bytes:
    """
    Renders the report as PDF bytes from a template context.
    """
    template = env.get_template(os.path.basename(TEMPLATE_DIR))
    html_content = template.render(**context)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


async def generate_patient_pdf(data: dict) -> BytesIO:
    """
    Build a clean context from raw FHIR data and render a PDF.

    data: {
        patient: {...},
        observations: [...],
        allergies: [...],
        conditions: [...],
        treatments: [...],
        immunizations: [...]
    }
    """
    patient = data.get("patient", {})
    observations = data.get("observations", [])
    allergies = data.get("allergies", [])
    conditions = data.get("conditions", [])
    treatments = data.get("treatments", [])
    immunizations = data.get("immunizations", [])

    context = {
        "patient_name": format_patient_name(patient),
        "birth_date": patient.get("birthDate", ""),
        "today": datetime.utcnow().strftime("%d/%m/%Y"),
        "observations": format_resources(observations, "effectiveDateTime", "valueString"),
        "allergies": format_resources(allergies, "recordedDate", "code.text"),
        "conditions": format_resources(conditions, "onsetDateTime", "code.text"),
        "treatments": format_resources(treatments, "authoredOn", "medicationCodeableConcept.text"),
        "immunizations": format_resources(immunizations, "occurrenceDateTime", "vaccineCode.text"),
    }

    pdf_content = render_patient_pdf(context)
    return BytesIO(pdf_content)


def format_patient_name(patient):
    names = patient.get("name", [])
    if not names:
        return "(Unnamed Patient)"
    name = names[0]
    given = " ".join(name.get("given", []))
    family = name.get("family", "")
    return f"{given} {family}".strip()


def format_resources(resources, date_field, text_field):
    result = []
    for r in resources:
        date = r.get(date_field)
        if not date:
            continue
        text = r
        for part in text_field.split('.'):
            text = text.get(part, {})
            if isinstance(text, str):
                break
        if isinstance(text, dict):
            text = "(No description)"
        result.append({
            "date": date,
            "text": text or "(No description)"
        })
    result.sort(key=lambda x: x["date"], reverse=True)
    return result
