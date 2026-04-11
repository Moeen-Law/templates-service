from app.services.contract_service import ContractService


def test_placeholder_validation_reports_bidirectional_mismatch():
    errors = ContractService._validate_placeholders(
        template_placeholders={"client_name", "company_name"},
        field_names={"client_name", "start_date"},
    )

    assert len(errors) == 2
    assert {error["field"] for error in errors} == {"company_name", "start_date"}
    assert {error["type"] for error in errors} == {"template_mismatch"}
