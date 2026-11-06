"""<<entity>> CompanyProfile - an interior designer's company information (spec item 2)."""
from app.db import get_db
from app.entity.base import now_str


class CompanyProfile:
    def __init__(self, designerID, companyName="", uen="", address="", phone="", email="", website="",
                 description="", updatedDate=None):
        self.designerID = designerID
        self.companyName = companyName
        self.uen = uen
        self.address = address
        self.phone = phone
        self.email = email
        self.website = website
        self.description = description
        self.updatedDate = updatedDate

    @staticmethod
    def findByDesigner(designerID):
        r = get_db().execute("SELECT * FROM company_profile WHERE designer_id = ?", (designerID,)).fetchone()
        if r is None:
            return None
        return CompanyProfile(r["designer_id"], r["company_name"], r["uen"], r["address"], r["phone"], r["email"],
                              r["website"], r["description"], r["updated_date"])

    def saveCompanyProfile(self):
        """Create or update the designer's company information."""
        self.updatedDate = now_str()
        db = get_db()
        db.execute("INSERT INTO company_profile (designer_id, company_name, uen, address, phone, email, website, "
                   "description, updated_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                   "ON CONFLICT(designer_id) DO UPDATE SET company_name = excluded.company_name, uen = excluded.uen, "
                   "address = excluded.address, phone = excluded.phone, email = excluded.email, "
                   "website = excluded.website, description = excluded.description, updated_date = excluded.updated_date",
                   (self.designerID, self.companyName, self.uen, self.address, self.phone, self.email, self.website,
                    self.description, self.updatedDate))
        db.commit()
        return True
