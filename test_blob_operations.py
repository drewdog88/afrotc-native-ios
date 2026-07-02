import os
import unittest
import tempfile
from datetime import datetime
from app_local import app, db, RecruitmentDocument
from vercel_blob import put, list as blob_list, delete, head
from sqlalchemy import text

class TestBlobOperations(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        with app.app_context():
            # Clean database
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()
            
            # Create all tables
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()

    def test_blob_put_operation(self):
        """Test uploading a file to Vercel Blob storage"""
        with app.app_context():
            # Create a test file
            test_content = b"This is a test file for Vercel Blob storage"
            test_filename = f"test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            try:
                # Upload to blob storage
                blob_response = put(test_filename, test_content, {"addRandomSuffix": False})
                
                # Verify response structure
                self.assertIsInstance(blob_response, dict)
                self.assertIn('url', blob_response)
                self.assertIsNotNone(blob_response['url'])
                self.assertTrue(blob_response['url'].startswith('https://'))
                
                print(f"✅ Successfully uploaded file: {blob_response['url']}")
                
                # Clean up - delete the test file
                delete(blob_response['url'], {})
                
            except Exception as e:
                self.fail(f"Blob put operation failed: {str(e)}")

    def test_blob_head_operation(self):
        """Test getting metadata from Vercel Blob storage"""
        with app.app_context():
            # Create a test file
            test_content = b"This is a test file for metadata testing"
            test_filename = f"test_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            try:
                # Upload to blob storage
                blob_response = put(test_filename, test_content, {"addRandomSuffix": False})
                blob_url = blob_response['url']
                
                # Get metadata
                blob_meta = head(blob_url, {})
                
                # Verify metadata structure
                self.assertIsInstance(blob_meta, dict)
                self.assertIn('size', blob_meta)
                self.assertEqual(blob_meta['size'], len(test_content))
                
                print(f"✅ Successfully retrieved metadata: size={blob_meta['size']} bytes")
                
                # Clean up
                delete(blob_url, {})
                
            except Exception as e:
                self.fail(f"Blob head operation failed: {str(e)}")

    def test_blob_delete_operation(self):
        """Test deleting a file from Vercel Blob storage"""
        with app.app_context():
            # Create a test file
            test_content = b"This is a test file for deletion testing"
            test_filename = f"test_delete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            try:
                # Upload to blob storage
                blob_response = put(test_filename, test_content, {"addRandomSuffix": False})
                blob_url = blob_response['url']
                
                # Verify file exists by getting metadata
                blob_meta = head(blob_url, {})
                self.assertIsNotNone(blob_meta)
                
                # Delete the file
                delete(blob_url, {})
                
                print(f"✅ Successfully deleted file: {blob_url}")
                
                # Verify file is deleted by trying to get metadata (should fail)
                try:
                    head(blob_url, {})
                    self.fail("File should have been deleted but still exists")
                except Exception:
                    # This is expected - file should not exist
                    pass
                
            except Exception as e:
                self.fail(f"Blob delete operation failed: {str(e)}")

    def test_document_upload_flow(self):
        """Test the complete document upload flow using Blob storage"""
        with app.app_context():
            # Create test document content
            test_content = b"This is a test document for the recruitment system"
            test_filename = "test_recruitment_doc.pdf"
            
            try:
                # Simulate document upload (like in add_document route)
                unique_filename = f"documents/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{test_filename}"
                
                # Upload to blob storage
                blob_response = put(unique_filename, test_content, {"addRandomSuffix": False})
                blob_url = blob_response['url']
                
                # Create database record
                document = RecruitmentDocument(
                    title='Test Recruitment Document',
                    description='Test document for blob storage testing',
                    filename=unique_filename,
                    original_filename=test_filename,
                    file_size=len(test_content),
                    file_type='pdf',
                    category='test'
                )
                db.session.add(document)
                db.session.commit()
                
                # Verify database record
                retrieved_doc = RecruitmentDocument.query.filter_by(title='Test Recruitment Document').first()
                self.assertIsNotNone(retrieved_doc)
                self.assertEqual(retrieved_doc.filename, unique_filename)
                self.assertEqual(retrieved_doc.file_size, len(test_content))
                
                # Verify blob file exists
                blob_meta = head(blob_url, {})
                self.assertEqual(blob_meta['size'], len(test_content))
                
                print(f"✅ Successfully completed document upload flow")
                
                # Clean up
                delete(blob_url, {})
                db.session.delete(retrieved_doc)
                db.session.commit()
                
            except Exception as e:
                self.fail(f"Document upload flow failed: {str(e)}")

    def test_document_download_flow(self):
        """Test the complete document download flow from Blob storage"""
        with app.app_context():
            # Create test document
            test_content = b"This is a test document for download testing"
            test_filename = "test_download_doc.pdf"
            unique_filename = f"documents/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{test_filename}"
            
            try:
                # Upload to blob storage
                blob_response = put(unique_filename, test_content, {"addRandomSuffix": False})
                blob_url = blob_response['url']
                
                # Create database record
                document = RecruitmentDocument(
                    title='Test Download Document',
                    description='Test document for download testing',
                    filename=unique_filename,
                    original_filename=test_filename,
                    file_size=len(test_content),
                    file_type='pdf',
                    category='test'
                )
                db.session.add(document)
                db.session.commit()
                
                # Test download flow (simulate download_document route)
                retrieved_doc = RecruitmentDocument.query.get(document.id)
                self.assertIsNotNone(retrieved_doc)
                
                # Verify we can get blob metadata (simulating download preparation)
                blob_meta = head(blob_url, {})
                self.assertEqual(blob_meta['size'], len(test_content))
                
                print(f"✅ Successfully completed document download flow preparation")
                
                # Clean up
                delete(blob_url, {})
                db.session.delete(retrieved_doc)
                db.session.commit()
                
            except Exception as e:
                self.fail(f"Document download flow failed: {str(e)}")

    def test_document_deletion_flow(self):
        """Test the complete document deletion flow including Blob cleanup"""
        with app.app_context():
            # Create test document
            test_content = b"This is a test document for deletion flow testing"
            test_filename = "test_deletion_doc.pdf"
            unique_filename = f"documents/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{test_filename}"
            
            try:
                # Upload to blob storage
                blob_response = put(unique_filename, test_content, {"addRandomSuffix": False})
                blob_url = blob_response['url']
                
                # Create database record
                document = RecruitmentDocument(
                    title='Test Deletion Document',
                    description='Test document for deletion flow testing',
                    filename=unique_filename,
                    original_filename=test_filename,
                    file_size=len(test_content),
                    file_type='pdf',
                    category='test'
                )
                db.session.add(document)
                db.session.commit()
                document_id = document.id
                
                # Verify document exists
                retrieved_doc = RecruitmentDocument.query.get(document_id)
                self.assertIsNotNone(retrieved_doc)
                
                # Verify blob file exists
                blob_meta = head(blob_url, {})
                self.assertIsNotNone(blob_meta)
                
                # Test deletion flow (simulate delete_document route)
                # Delete from blob storage
                delete(blob_url, {})
                
                # Delete from database
                db.session.delete(retrieved_doc)
                db.session.commit()
                
                # Verify database record is deleted
                deleted_doc = RecruitmentDocument.query.get(document_id)
                self.assertIsNone(deleted_doc)
                
                # Verify blob file is deleted
                try:
                    head(blob_url, {})
                    self.fail("Blob file should have been deleted but still exists")
                except Exception:
                    # This is expected - file should not exist
                    pass
                
                print(f"✅ Successfully completed document deletion flow")
                
            except Exception as e:
                self.fail(f"Document deletion flow failed: {str(e)}")

    def test_blob_error_handling(self):
        """Test error handling for invalid Blob operations"""
        with app.app_context():
            try:
                # Test getting metadata for non-existent file
                fake_url = "https://example.com/nonexistent.txt"
                
                try:
                    head(fake_url, {})
                    self.fail("Should have failed for non-existent file")
                except Exception as e:
                    print(f"✅ Correctly handled error for non-existent file: {str(e)}")
                
                # Test deleting non-existent file
                try:
                    delete(fake_url, {})
                    # Note: delete might not fail for non-existent files in some storage systems
                    print(f"✅ Delete operation completed (may not fail for non-existent files)")
                except Exception as e:
                    print(f"✅ Correctly handled delete error: {str(e)}")
                    
            except Exception as e:
                self.fail(f"Error handling test failed: {str(e)}")

    def test_blob_storage_environment(self):
        """Test that Blob storage environment is properly configured"""
        # Check that we have the required environment variable
        blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
        self.assertIsNotNone(blob_token, "BLOB_READ_WRITE_TOKEN environment variable is not set")
        self.assertTrue(len(blob_token) > 0, "BLOB_READ_WRITE_TOKEN is empty")
        
        print(f"✅ Blob storage environment properly configured")

if __name__ == '__main__':
    unittest.main()
