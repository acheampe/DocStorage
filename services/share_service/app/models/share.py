from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

class SharedDocument(db.Model):
    __tablename__ = 'shareddocuments'

    share_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    shared_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    permissions = db.Column(JSONB, nullable=False, default={
        "can_view": True,
        "can_download": False,
        "can_reshare": False
    })
    status = db.Column(db.String(20), nullable=False, default='active')

    def to_dict(self):
        return {
            'share_id': self.share_id,
            'doc_id': self.doc_id,
            'owner_id': self.owner_id,
            'recipient_id': self.recipient_id,
            'shared_date': self.shared_date.isoformat() if self.shared_date else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'permissions': self.permissions,
            'status': self.status
        } 