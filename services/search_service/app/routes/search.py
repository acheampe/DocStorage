from flask import Blueprint, request, jsonify
from ..models.document_index import DocumentIndex
from ..models.shared_documents import SharedDocuments
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
        user_id = request.args.get('user_id', type=int)
        print(f"Search service received query: {query} for user: {user_id}")

        # Search owned documents
        owned_results = DocumentIndex.search(query).filter_by(owner_id=user_id).all()

        # Search shared documents
        shared_results = DocumentIndex.query.join(SharedDocuments, DocumentIndex.doc_id == SharedDocuments.doc_id)\
            .filter((SharedDocuments.owner_id == user_id) | (SharedDocuments.recipient_id == user_id))\
            .filter(DocumentIndex.search_vector.match(query)).all()

        results = owned_results + shared_results
        print(f"Search results: {results}")

        return jsonify({
            'results': [result.to_dict() for result in results],
            'debug_info': {
                'query': query,
                'total_indexed': len(results)
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

@search_bp.route('/search/delete/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    try:
        print(f"Search service: Attempting to delete document {doc_id}")
        doc = DocumentIndex.query.filter_by(doc_id=doc_id).first()
        
        if doc:
            db.session.delete(doc)
            db.session.commit()
            print(f"Search service: Successfully deleted document {doc_id}")
            return jsonify({'message': 'Document removed from search index'})
        else:
            print(f"Search service: Document {doc_id} not found in index")
            return jsonify({'message': 'Document not found in search index'}), 404
            
    except Exception as e:
        print(f"Search service error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete document from search index'}), 500 