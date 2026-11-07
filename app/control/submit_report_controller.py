"""<<control>> SubmitReportController - a customer reports an inappropriate IDP (input for #38)."""
import os
import uuid
from flask import current_app
from app.entity.report import Report
from app.entity.idp import IDP
from app.entity.notification import Notification
from app.entity.user_account import UserAccount
from app.constants import REPORT_REASONS, IDP_ACTIVE, CUSTOMER, PLATFORM_MANAGER

ALLOWED_EXT = {".jpg", ".jpeg", ".png"}
MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
MAX_DESCRIPTION = 1000


class SubmitReportController:
    def __init__(self):
        self.errorMsgs = []

    def getReasons(self):
        return REPORT_REASONS

    def getReportableIDP(self, idpID):
        """Only active projects can be reported."""
        idp = IDP.getIDPDetails(idpID)
        return idp if idp is not None and idp.status == IDP_ACTIVE else None

    def submitReport(self, customer, idp, reason, description="", evidence=None):
        """Validate and save the report, then notify every Platform Manager.
        `evidence` is an optional uploaded photo. Returns the new Report or None (with errorMsgs)."""
        evidence = evidence if evidence is not None and getattr(evidence, "filename", "") else None
        if not self._validateReport(customer, idp, reason, description, evidence):
            return None
        report = Report(None, idp.idpID, customer.accountID, reason, (description or "").strip())
        if evidence is not None:
            report.evidenceURLs = [self._saveEvidence(evidence)]
        report.createReport()
        for pm in UserAccount.findIDsByProfile(PLATFORM_MANAGER):
            Notification.send(pm, f"New report about '{idp.title}'",
                              f"{customer.name} reported this project for: {reason}.")
        return report

    def _validateReport(self, customer, idp, reason, description, evidence):
        errors = []
        if customer is None or customer.profileName != CUSTOMER:
            errors.append("Only customers can report projects.")
        if idp is None or idp.status != IDP_ACTIVE:
            errors.append("This project can no longer be reported.")
        elif customer is not None and Report.hasPendingReport(customer.accountID, idp.idpID):
            errors.append("You have already reported this project. The Platform Manager is reviewing it.")
        if reason not in REPORT_REASONS:
            errors.append("Please select a reason.")
        if len(description or "") > MAX_DESCRIPTION:
            errors.append(f"Description must be {MAX_DESCRIPTION} characters or fewer.")
        if evidence is not None:
            ext = os.path.splitext(evidence.filename)[1].lower()
            if ext not in ALLOWED_EXT:
                errors.append("Evidence must be a JPG or PNG image.")
            elif self._fileSize(evidence) >= MAX_EVIDENCE_BYTES:
                errors.append("Evidence must be under 5 MB.")
        self.errorMsgs = errors
        return not errors

    @staticmethod
    def _fileSize(fileStorage):
        stream = fileStorage.stream
        pos = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(pos)
        return size

    @staticmethod
    def _saveEvidence(fileStorage):
        ext = os.path.splitext(fileStorage.filename)[1].lower()
        name = f"report_{uuid.uuid4().hex[:12]}{ext}"
        folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(folder, exist_ok=True)
        fileStorage.save(os.path.join(folder, name))
        return name
