from django.test import TestCase

from .models import AuditLog, Company


class AuditLogTests(TestCase):
    def test_entry_cannot_be_modified_or_deleted_through_instance(self):
        company = Company.objects.create(name="Demo", ruc="20999999991")
        entry = AuditLog.objects.create(company=company, action="TEST", entity="Company")
        entry.action = "ALTERED"
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()
