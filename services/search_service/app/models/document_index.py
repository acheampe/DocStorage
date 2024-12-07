from .. import db
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy import text

class DocumentIndex(db.Model):
    __tablename__ = 'documentindex'
    
    index_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, nullable=False, unique=True)
    content_text = db.Column(db.Text, server_default='')
    doc_metadata = db.Column(JSONB, server_default='{}')
    last_indexed = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    search_vector = db.Column(
        TSVECTOR,
        server_default=text("""
            to_tsvector('english',
                COALESCE(content_text, '') || ' ' ||
                regexp_replace(COALESCE(doc_metadata->>'filename', ''), '[_.]', ' ', 'g') || ' ' ||
                COALESCE(doc_metadata->>'description', '')
            )
        """),
        nullable=False
    )

    def __repr__(self):
        return f'<DocumentIndex {self.doc_id}>'