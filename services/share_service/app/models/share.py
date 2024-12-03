from datetime import datetime
from app import db

class SharedDocument(db.Model):
    __tablename__ = 'shareddocuments'

    share_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    shared_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default='active')

    def to_dict(self):
        return {
            'share_id': self.share_id,
            'doc_id': self.doc_id,
            'owner_id': self.owner_id,
            'recipient_id': self.recipient_id,
            'display_name': self.display_name,
            'original_filename': self.original_filename,
            'shared_date': self.shared_date.isoformat() if self.shared_date else None,
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
 