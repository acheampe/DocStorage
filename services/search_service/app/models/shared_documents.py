from .. import db
from datetime import datetime

class SharedDocuments(db.Model):
    __bind_key__ = 'share_db'
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
    file_path = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        db.Index('idx_owner_id', 'owner_id'),
        db.Index('idx_recipient_id', 'recipient_id'),
        db.Index('idx_shared_docs_doc', 'doc_id'),
        db.Index('idx_shared_docs_status', 'status'),
        db.UniqueConstraint('doc_id', 'owner_id', 'recipient_id', name='idx_unique_share')
    ) 