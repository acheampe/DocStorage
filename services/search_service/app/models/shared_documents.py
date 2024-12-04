from .. import db

class SharedDocuments(db.Model):
    __tablename__ = 'shareddocuments'

    share_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active') 