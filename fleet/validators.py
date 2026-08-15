from pathlib import Path

from django.core.exceptions import ValidationError


MAX_EVIDENCE_SIZE = 10 * 1024 * 1024
MAX_IMPORT_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_evidence_file(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Solo se permiten evidencias PDF, JPG y PNG.")
    if upload.size > MAX_EVIDENCE_SIZE:
        raise ValidationError("El archivo supera el máximo permitido de 10 MB.")
    position = upload.tell()
    header = upload.read(16)
    upload.seek(position)
    if not any(header.startswith(signature) for signature in SIGNATURES[extension]):
        raise ValidationError("El contenido del archivo no coincide con su extensión.")


def validate_excel_import(upload):
    if Path(upload.name).suffix.lower() != ".xlsx":
        raise ValidationError("La importación requiere un archivo .xlsx.")
    if upload.size > MAX_IMPORT_SIZE:
        raise ValidationError("El Excel supera el máximo permitido de 5 MB.")
    position = upload.tell()
    header = upload.read(4)
    upload.seek(position)
    if header != b"PK\x03\x04":
        raise ValidationError("El contenido no corresponde a un archivo Excel .xlsx válido.")
