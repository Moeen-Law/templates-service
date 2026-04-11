import tempfile
from typing import Any

from docxtpl import DocxTemplate


class RenderService:
    @staticmethod
    def extract_placeholders(docx_bytes: bytes) -> set[str]:
        with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
            tmp.write(docx_bytes)
            tmp.flush()
            template = DocxTemplate(tmp.name)
            variables = template.get_undeclared_template_variables()
        return set(variables)

    @staticmethod
    def render_docx(docx_bytes: bytes, data: dict[str, Any]) -> bytes:
        with tempfile.NamedTemporaryFile(
            suffix=".docx"
        ) as template_file, tempfile.NamedTemporaryFile(suffix=".docx") as output_file:
            template_file.write(docx_bytes)
            template_file.flush()

            document = DocxTemplate(template_file.name)
            document.render(data)
            document.save(output_file.name)
            output_file.seek(0)
            return output_file.read()
