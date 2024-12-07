from app import create_app, db
import psycopg2
import json

app = create_app()

def update_index():
    try:
        # Connect to document service database
        doc_conn = psycopg2.connect(
            dbname='dSDocMgmtService',
            user='emac',
            host='localhost',
            port='5432'
        )
        
        with app.app_context():
            with doc_conn.cursor() as cur:
                # Get all documents
                cur.execute("""
                    SELECT doc_id, original_filename, file_type, file_path
                    FROM documents
                """)
                
                for doc in cur.fetchall():
                    doc_id, original_filename, file_type, file_path = doc
                    
                    # Update or insert into search index
                    db.session.execute("""
                        INSERT INTO documentindex (doc_id, content_text, doc_metadata)
                        VALUES (:doc_id, :content_text, :metadata)
                        ON CONFLICT (doc_id) DO UPDATE SET
                            content_text = :content_text,
                            doc_metadata = :metadata,
                            last_indexed = CURRENT_TIMESTAMP
                    """, {
                        'doc_id': doc_id,
                        'content_text': original_filename,  # You might want to add actual file content here
                        'metadata': json.dumps({
                            'filename': original_filename,
                            'file_type': file_type,
                            'file_path': file_path
                        })
                    })
                
                db.session.commit()
                print("Search index updated successfully")
                
    except Exception as e:
        print(f"Error updating index: {str(e)}")
        db.session.rollback()
        raise
    finally:
        doc_conn.close()

if __name__ == "__main__":
    update_index() 