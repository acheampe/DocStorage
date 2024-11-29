from ..extensions import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'

    doc_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        """
        Convert the document object to a dictionary for JSON serialization
        """
        return {
            'doc_id': self.doc_id,
            'filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'upload_date': self.upload_date.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'description': self.description
        }
