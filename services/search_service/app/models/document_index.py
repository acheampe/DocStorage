from .. import db
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy import Index, text, Computed
from sqlalchemy.sql import func
from datetime import datetime
import traceback

class DocumentIndex(db.Model):
    __tablename__ = 'documentindex'
    
    index_id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, unique=True, nullable=False)
    content_text = db.Column(db.Text, default='')
    doc_metadata = db.Column(JSONB, default={})
    last_indexed = db.Column(db.DateTime, default=datetime.utcnow)
    search_vector = db.Column(
        TSVECTOR,
        Computed("""
            to_tsvector('english',
                coalesce(content_text, '') || ' ' ||
                regexp_replace(coalesce(doc_metadata->>'filename', ''), '[_.]', ' ', 'g') || ' ' ||
                coalesce(doc_metadata->>'description', '')
            )
        """),
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_document_search', 'search_vector', postgresql_using='gin'),
    )
    
    @classmethod
    def search(cls, query_text):
        try:
            # Process the query text to handle partial matches
            processed_query = ' | '.join(query_text.split('_'))  # Split on underscores
            print(f"Original query: {query_text}")
            print(f"Processed query: {processed_query}")
            
            # Use websearch_to_tsquery for more flexible matching
            ts_query = func.websearch_to_tsquery('english', processed_query)
            
            results = db.session.query(
                cls,
                func.ts_rank(cls.search_vector, ts_query).label('rank')
            ).filter(
                cls.search_vector.op('@@')(ts_query)
            ).order_by(
                text('rank DESC')
            ).limit(20).all()
            
            print(f"Query text: {query_text}")
            print(f"Total results: {len(results)}")
            print(f"Raw results: {results}")
            
            return [{
                'doc_id': result[0].doc_id,
                'metadata': result[0].doc_metadata,
                'last_indexed': result[0].last_indexed.isoformat() if result[0].last_indexed else None,
                'rank': float(result[1])
            } for result in results]
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def to_dict(self):
        return {
            'doc_id': self.doc_id,
            'metadata': self.doc_metadata,
            'last_indexed': self.last_indexed.isoformat() if self.last_indexed else None
        }
    
    def update_search_vector(self):
        self.last_indexed = datetime.utcnow()