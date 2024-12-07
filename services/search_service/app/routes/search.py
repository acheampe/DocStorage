from flask import Blueprint, request, jsonify, current_app
from ..models.document_index import DocumentIndex
from .. import db
from ..utils.auth import require_auth, get_forwarded_headers
import traceback
from sqlalchemy import text
import jwt
import json
import os
import requests

search_bp = Blueprint('search', __name__)

@search_bp.route('/index', methods=['POST'])
def index_document():
    try:
        data = request.get_json()
        print(f"\nIndexing request for doc_id: {data.get('doc_id')}")
        
        if not data or 'doc_id' not in data:
            return jsonify({'error': 'Invalid request data'}), 400

        # Extract metadata and content
        metadata = data.get('doc_metadata', {})
        content = data.get('content_text', '')
        
        # Create or update document index WITHOUT setting search_vector
        doc_index = DocumentIndex(
            doc_id=data['doc_id'],
            content_text=content,
            doc_metadata=metadata
            # Remove search_vector - it will be generated automatically
        )
        
        print(f"Created index for document {data['doc_id']}")
        print(f"Metadata: {metadata}")
        
        db.session.merge(doc_index)
        db.session.commit()
        
        return jsonify({'message': 'Document indexed successfully'})
        
    except Exception as e:
        print(f"Indexing error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/search', methods=['GET'])
@require_auth
def search_documents(current_user):
    try:
        # Normalize query by replacing spaces with underscores and vice versa
        query = request.args.get('q', '').strip()
        normalized_query = query.replace(' ', '_').lower()
        space_query = query.replace('_', ' ').lower()
        
        user_id = current_user['user_id']
        
        print(f"\n=== Search Debug ===")
        print(f"User ID: {user_id}")
        print(f"Raw query: '{query}'")

        if not query:
            return jsonify({'results': [], 'count': 0})

        # Initialize empty dictionary for shared docs
        shared_doc_map = {}

        # Get shared documents
        share_engine = db.get_engine(bind='share_db')
        shared_docs_query = text("""
            SELECT doc_id, share_id, owner_id as shared_by, shared_date
            FROM shareddocuments
            WHERE recipient_id = :user_id AND status = 'active'
        """)

        with share_engine.connect() as conn:
            shared_docs = conn.execute(shared_docs_query, {'user_id': user_id}).fetchall()
            
            # Safely convert shared docs to dictionary
            shared_doc_map = {
                doc.doc_id: {
                    'share_id': doc.share_id,
                    'shared_by': doc.shared_by,
                    'shared_date': doc.shared_date
                } for doc in shared_docs
            } if shared_docs else {}

        print(f"Found {len(shared_doc_map)} shared documents")

        # Modified search query
        search_query = text("""
            SELECT DISTINCT ON (di.doc_id)
                di.doc_id,
                di.doc_metadata,
                di.content_text
            FROM documentindex di
            WHERE
                (
                    LOWER(di.doc_metadata->>'original_filename') LIKE :underscore_query
                    OR LOWER(di.doc_metadata->>'original_filename') LIKE :space_query
                    OR LOWER(di.doc_metadata->>'filename') LIKE :underscore_query
                    OR LOWER(di.doc_metadata->>'filename') LIKE :space_query
                )
                AND (
                    di.doc_metadata->>'user_id' = :user_id
                    OR di.doc_id = ANY(:shared_ids)
                )
            ORDER BY di.doc_id
        """)

        results = db.session.execute(
            search_query,
            {
                'underscore_query': f'%{normalized_query}%',
                'space_query': f'%{space_query}%',
                'user_id': str(user_id),
                'shared_ids': list(shared_doc_map.keys()) or [-1]
            }
        ).fetchall()

        print(f"Found {len(results) if results else 0} matching documents")

                # Format results
        formatted_results = []
        seen_keys = set()
        
        for row in results:
            # Create a unique key for each result using doc_id and share_id
            unique_key = (row.doc_id, shared_doc_map.get(row.doc_id, {}).get('share_id', None))
            
            if unique_key not in seen_keys:
                seen_keys.add(unique_key)
                
                # Safely access metadata and share info
                metadata = row.doc_metadata or {}
                share_info = shared_doc_map.get(row.doc_id, {})
                
                formatted_results.append({
                    'doc_id': row.doc_id,
                    'original_filename': metadata.get('original_filename'),
                    'upload_date': metadata.get('upload_date'),
                    'file_type': metadata.get('file_type'),
                    'content': row.content_text[:200] if row.content_text else None,
                    'is_shared': row.doc_id in shared_doc_map,
                    'shared_by': share_info.get('shared_by'),
                    'share_id': share_info.get('share_id')
                })


        # Split query into words and check if all words are in filename
        query_words = query.lower().split()
        filtered_results = [
            result for result in formatted_results
            if result['original_filename'] and all(
                word in result['original_filename'].lower().replace('_', ' ')
                for word in query_words
            )
        ]

        print(f"Filtered Results: {filtered_results}")

        return jsonify({
            'results': filtered_results,
            'count': len(filtered_results)
        })

    except Exception as e:
        print(f"\n=== Search Error ===")
        print(f"User ID: {user_id}")
        print(f"Query: '{query}'")
        print(f"Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500




@search_bp.route('/vectors', methods=['GET'])
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

@search_bp.route('/delete/<int:doc_id>', methods=['DELETE'])
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

@search_bp.route('/debug', methods=['GET'])
def debug_index():
    try:
        all_docs = text("""
            SELECT doc_id, content_text, doc_metadata 
            FROM documentindex
        """)
        results = db.session.execute(all_docs).fetchall()
        
        print("\nAll indexed documents:")
        for row in results:
            print(f"Doc ID: {row.doc_id}")
            print(f"Metadata: {row.doc_metadata}")
            print(f"Content: {row.content_text[:100]}...")
            print("---")
            
        return jsonify([{
            'doc_id': row.doc_id,
            'metadata': row.doc_metadata,
            'content_preview': row.content_text[:100] if row.content_text else None
        } for row in results])
    except Exception as e:
        print(f"Debug index error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/reindex', methods=['POST'])
def reindex_all():
    try:
        # Get engine for doc_db
        doc_engine = db.get_engine(bind='doc_db')
        print(f"Starting reindex of all documents")

        # First, clear existing index
        db.session.execute(text("TRUNCATE TABLE documentindex"))
        db.session.commit()
        
        # Get all documents
        all_docs_query = text("""
            SELECT doc_id, filename, original_filename, upload_date, 
                   file_type, description, user_id, last_modified
            FROM documents
        """)
        
        with doc_engine.connect() as conn:
            documents = conn.execute(all_docs_query).fetchall()
            
        print(f"Found {len(documents)} documents to reindex")
            
        for doc in documents:
            # Create document index without search_vector
            doc_index = DocumentIndex(
                doc_id=doc.doc_id,
                doc_metadata={
                    'filename': doc.filename,
                    'original_filename': doc.original_filename,
                    'upload_date': doc.upload_date.isoformat() if doc.upload_date else None,
                    'file_type': doc.file_type,
                    'description': doc.description,
                    'user_id': doc.user_id,
                    'last_modified': doc.last_modified.isoformat() if doc.last_modified else None
                },
                content_text=f"File: {doc.filename}"  # Basic content text
            )
            db.session.add(doc_index)  # Using add instead of merge
            print(f"Indexed document {doc.doc_id}: {doc.filename}")
            
        db.session.commit()
        return jsonify({'message': f'Reindexed {len(documents)} documents'})
        
    except Exception as e:
        print(f"Reindex error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/debug/search/<term>', methods=['GET'])
def debug_search(term):
    try:
        print(f"\nDebug search for term: '{term}'")
        debug_query = text("""
            SELECT 
                doc_id,
                doc_metadata,
                content_text,
                search_vector,
                ts_rank_cd(search_vector, to_tsquery('english', :query)) as rank
            FROM documentindex
            WHERE search_vector @@ to_tsquery('english', :query)
            ORDER BY rank DESC
        """)
        
        results = db.session.execute(
            debug_query,
            {'query': term + ':*'}
        ).fetchall()
        
        print(f"Found {len(results)} matches in index")
        for idx, row in enumerate(results):
            print(f"\nMatch {idx + 1}:")
            print(f"Doc ID: {row.doc_id}")
            print(f"Metadata: {row.doc_metadata}")
            print(f"Rank: {row.rank}")
        
        return jsonify({
            'query': term,
            'results': [{
                'doc_id': row.doc_id,
                'metadata': row.doc_metadata,
                'content_preview': row.content_text[:100] if row.content_text else None,
                'search_vector': str(row.search_vector),
                'rank': float(row.rank)
            } for row in results]
        })
        
    except Exception as e:
        print(f"Debug search error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500