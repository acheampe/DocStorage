from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import JSONB

class SharedDocument(db.Model):
    __tablename__ = 'shared_documents'

    share_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    can_view = db.Column(db.Boolean, default=True)
    can_download = db.Column(db.Boolean, default=False)
    can_reshare = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='active')

    def to_dict(self):
        return {
            'share_id': self.share_id,
            'doc_id': self.doc_id,
            'owner_id': self.owner_id,
            'recipient_email': self.recipient_email,
            'permissions': {
                'can_view': self.can_view,
                'can_download': self.can_download,
                'can_reshare': self.can_reshare
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status
        }

    def is_active(self):
        return (
            self.status == 'active' and
            (self.expiry_date is None or self.expiry_date > datetime.utcnow())
        )

    def update_last_accessed(self):
        self.last_accessed = datetime.utcnow()
 