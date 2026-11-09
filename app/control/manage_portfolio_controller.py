"""<<control>> ManagePortfolioController - User Story #13 Manage Portfolio."""
import os
import uuid
from datetime import date, datetime
from flask import current_app
from app.entity.idp import IDP
from app.entity.idp_cost_item import IDPCostItem, UNITS
from app.constants import IDP_ACTIVE, IDP_ARCHIVED, IDP_HIDDEN, PROPERTY_TYPES

ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
MAX_COST_ITEMS = 30
MAX_PHOTO_BYTES = 5 * 1024 * 1024


class ManagePortfolioController:
    def __init__(self):
        self.errorMsgs = []

    def getPortfolio(self, designerID):
        """Active projects (plus any hidden by the Platform Manager, so the designer can see them)."""
        return IDP.getIDPsByStatus(designerID, [IDP_ACTIVE, IDP_HIDDEN])

    def getInterestCounts(self, designerID):
        """Spec item 5 - views and times shortlisted for each of the designer's projects."""
        return IDP.getInterestCounts(designerID)

    def getArchivedIDPs(self, designerID):
        return IDP.getIDPsByStatus(designerID, IDP_ARCHIVED)

    def getIDP(self, idpID, designerID):
        """The IDP if it belongs to this designer, otherwise None."""
        idp = IDP.getIDPDetails(idpID)
        return idp if idp is not None and idp.designerID == designerID else None

    def editIDP(self, idp, newPhotos=None, removePhotos=None, costItems=None):
        """Validate and save the edited IDP. newPhotos are uploaded files
        (objects with .filename, .save(), and a readable stream). If costItems are given,
        they replace the cost breakdown and the total cost is recalculated."""
        newPhotos = [p for p in (newPhotos or []) if p and p.filename]
        ok = self._validateIDPDetails(idp, newPhotos, costItems)
        if not ok:
            return False
        idp.photoURLs = [u for u in idp.photoURLs if u not in set(removePhotos or [])]
        idp.photoURLs += [self._savePhoto(idp.idpID, p) for p in newPhotos]
        return idp.updateIDP(costItems)

    def createIDP(self, idp, costItems, newPhotos=None):
        """Add Project - a new listing with its cost breakdown. Returns the new ID or None."""
        newPhotos = [p for p in (newPhotos or []) if p and p.filename]
        if not self._validateIDPDetails(idp, newPhotos, costItems, requireItems=True):
            return None
        idp.createIDP(costItems)
        if newPhotos:
            idp.photoURLs = [self._savePhoto(idp.idpID, p) for p in newPhotos]
            idp.updateIDP()
        return idp.idpID

    def _validateIDPDetails(self, idp, newPhotos, costItems=None, requireItems=False):
        errors = []
        if not (idp.title or "").strip():
            errors.append("Title is required.")
        if not (idp.description or "").strip():
            errors.append("Description is required.")
        if idp.propertyType not in PROPERTY_TYPES:
            errors.append("Please select a property type.")
        if costItems is None and not requireItems:
            if idp.totalCost is None or idp.totalCost <= 0:
                errors.append("Total cost must be a positive number.")
        else:
            errors += self._validateCostItems(costItems or [])
        if idp.floorArea is None or idp.floorArea <= 0:
            errors.append("Floor area must be a positive number.")
        try:
            if not idp.completionDate:
                raise ValueError
            if datetime.strptime(idp.completionDate, "%Y-%m-%d").date() > date.today():
                errors.append("Completion date cannot be in the future.")
        except ValueError:
            errors.append("Please enter a valid completion date.")
        for p in newPhotos:
            ext = os.path.splitext(p.filename)[1].lower()
            if ext not in ALLOWED_EXT:
                errors.append(f"{p.filename}: photos must be JPG or PNG files.")
            elif self._fileSize(p) >= MAX_PHOTO_BYTES:
                errors.append(f"{p.filename}: photos must be under 5 MB.")
        self.errorMsgs = errors
        return not errors

    @staticmethod
    def _validateCostItems(items):
        """Each line needs an item name, a unit, and a positive quantity and unit rate."""
        errors = []
        if not items:
            errors.append("Please add at least one cost breakdown item.")
        if len(items) > MAX_COST_ITEMS:
            errors.append(f"A cost breakdown can have at most {MAX_COST_ITEMS} items.")
        for n, i in enumerate(items, 1):
            if not (i.itemName or "").strip():
                errors.append(f"Cost item {n}: please enter an item name.")
            if i.unit not in UNITS:
                errors.append(f"Cost item {n}: please select a unit.")
            if i.quantity is None or i.quantity <= 0:
                errors.append(f"Cost item {n}: quantity must be a positive number.")
            if i.unitRate is None or i.unitRate <= 0:
                errors.append(f"Cost item {n}: unit rate must be a positive number.")
        return errors

    @staticmethod
    def _fileSize(fileStorage):
        stream = fileStorage.stream
        pos = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(pos)
        return size

    @staticmethod
    def _savePhoto(idpID, fileStorage):
        ext = os.path.splitext(fileStorage.filename)[1].lower()
        name = f"idp{idpID}_{uuid.uuid4().hex[:10]}{ext}"
        folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(folder, exist_ok=True)
        fileStorage.save(os.path.join(folder, name))
        return name

    def archiveIDP(self, idpID, designerID):
        idp = self.getIDP(idpID, designerID)
        if idp is None or idp.status != IDP_ACTIVE:
            return False
        return IDP.updateStatus(idpID, IDP_ARCHIVED)

    def restoreIDP(self, idpID, designerID):
        idp = self.getIDP(idpID, designerID)
        if idp is None or idp.status != IDP_ARCHIVED:
            return False
        return IDP.updateStatus(idpID, IDP_ACTIVE)

    def deleteIDP(self, idpID, designerID):
        """Projects with reports are kept for the Platform Manager's records (#38)."""
        self.errorMsgs = []
        idp = self.getIDP(idpID, designerID)
        if idp is None:
            self.errorMsgs = ["Project not found."]
            return False
        if IDP.hasReports(idpID):
            self.errorMsgs = ["This project has user reports and cannot be deleted. You can archive it instead."]
            return False
        return IDP.deleteIDP(idpID)
