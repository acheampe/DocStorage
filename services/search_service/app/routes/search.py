from flask import Blueprint, request, jsonify
from ..models.document_index import DocumentIndex
from .. import db
import traceback

search_bp = Blueprint('search', __name__)

@search_bp.route('/search/index', methods=['POST'])
def index_document():
    try:
        data = request.get_json()
        print(f"Received indexing request with data: {data}")  # Debug log
        
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        if 'doc_id' not in data:
            print("Missing doc_id in request")
            return jsonify({'error': 'doc_id is required'}), 400
        
        doc_index = DocumentIndex(
            doc_id=data['doc_id'],
            content_text=data.get('content_text', ''),
            doc_metadata=data.get('doc_metadata', {})
        )
        
        print(f"Created DocumentIndex object: {doc_index.__dict__}")  # Debug log
        
        doc_index.update_search_vector()
        print("Updated search vector")  # Debug log
        
        db.session.merge(doc_index)
        print("Merged document into session")  # Debug log
        
        db.session.commit()
        print("Committed to database")  # Debug log
        
        return jsonify({'message': 'Document indexed successfully'})
        
    except Exception as e:
        print(f"Indexing error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")  # Full traceback
        db.session.rollback()
        return jsonify({
            'error': 'Indexing failed',
            'message': str(e),
            'type': type(e).__name__
        }), 500

@search_bp.route('/search', methods=['GET'])
def search_documents():
    try:
        query = request.args.get('q', '').strip()
        print(f"Search service received query: {query}")  # Debug log
        
        # Check if we have any documents indexed
        total_docs = DocumentIndex.query.count()
        print(f"Total indexed documents: {total_docs}")  # Debug log
        
        results = DocumentIndex.search(query)
        print(f"Search results: {results}")  # Debug log
        
        return jsonify({
            'results': results,
            'debug_info': {
                'query': query,
                'total_indexed': total_docs
            }
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500

@search_bp.route('/debug/vectors', methods=['GET'])
def debug_vectors():
    try:
        vectors = db.session.query(
            DocumentIndex.doc_id,
            DocumentIndex.doc_metadata,
            DocumentIndex.search_vector
        ).all()
        
        return jsonify([{
            'doc_id': v[0],
            'metadata': v[1],
            'vector': str(v[2])
        } for v in vectors])
    except Exception as e:
        return jsonify({'error': str(e)}), 500 