"""Unit tests for Manage Company Information (Interior Designer) and the public designer page."""
import pytest
from app.control.manage_company_profile_controller import ManageCompanyProfileController
from app.entity.company_profile import CompanyProfile
from tests.conftest import login
from tests.helpers import account_id, add_idp


def cp(**over):
    data = dict(companyName="Daniel Design Studio", uen="201912345K", address="1 Ubi Ave, Singapore 408933",
                phone="61234567", email="hello@danieldesign.sg", website="https://danieldesign.sg",
                description="Warm homes for families.")
    data.update(over)
    return CompanyProfile(account_id("designer"), **data)


def test_new_designer_gets_empty_profile(ctx):
    p = ManageCompanyProfileController().getCompanyProfile(account_id("designer"))
    assert p.companyName == "" and p.updatedDate is None


def test_save_and_update(ctx):
    c = ManageCompanyProfileController()
    assert c.updateCompanyProfile(cp()) is True
    assert c.updateCompanyProfile(cp(companyName="DD Studio")) is True       # update, not a second row
    saved = CompanyProfile.findByDesigner(account_id("designer"))
    assert saved.companyName == "DD Studio" and saved.updatedDate


@pytest.mark.parametrize("field,value,msg", [
    ("companyName", "", "Company name is required."),
    ("uen", "12AB", "UEN must be a valid Singapore UEN"),
    ("phone", "123", "Phone number must be 8 digits"),
    ("email", "nope", "Email is not in a valid format."),
    ("website", "danieldesign.sg", "Website must start with http"),
    ("description", "x" * 1001, "Description must be 1000 characters or fewer."),
])
def test_validation(ctx, field, value, msg):
    c = ManageCompanyProfileController()
    assert c.updateCompanyProfile(cp(**{field: value})) is False
    assert any(m.startswith(msg) for m in c.errorMsgs)


def test_optional_fields_can_be_blank(ctx):
    assert ManageCompanyProfileController().updateCompanyProfile(cp(uen="", website="", address="")) is True


def test_designer_page_data(ctx):
    add_idp(title="Shown")
    add_idp(title="Archived", status="Archived")
    ManageCompanyProfileController().updateCompanyProfile(cp())
    designer, company, projects = ManageCompanyProfileController().getDesignerPage(account_id("designer"))
    assert company.companyName == "Daniel Design Studio" and [p.title for p in projects] == ["Shown"]
    assert ManageCompanyProfileController().getDesignerPage(account_id("customer")) is None


def test_company_form_page(client):
    login(client, "designer")
    assert "Company Information" in client.get("/designer/company").get_data(as_text=True)
    html = client.post("/designer/company", data={"company_name": "DD Studio", "uen": "201912345k",
                                                  "phone": "61234567", "email": "a@b.sg"}).get_data(as_text=True)
    assert "Company information saved" in html


def test_company_shown_on_project_and_designer_pages(client, app):
    with app.app_context():
        iid = add_idp(title="Studio Project")
        ManageCompanyProfileController().updateCompanyProfile(cp())
        did = account_id("designer")
    assert "Daniel Design Studio" in client.get(f"/projects/{iid}").get_data(as_text=True)
    html = client.get(f"/designers/{did}").get_data(as_text=True)
    assert "Daniel Design Studio" in html and "Studio Project" in html


def test_only_designers_edit_company(client):
    login(client, "customer")
    assert client.get("/designer/company").status_code == 403
