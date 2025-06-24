import unittest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from flask import Flask
from app import create_app
from models.jobber_models import JobberClient, JobberJob, JobberInvoice


class TestJobberWebhooks(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app(testing=True)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Mock webhook secret
        self.webhook_secret = "test_webhook_secret"
        self.app.config['JOBBER_WEBHOOK_SECRET'] = self.webhook_secret

    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()

    def _generate_signature(self, payload):
        """Generate HMAC signature for webhook payload"""
        return hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_webhook_request(self, payload_data, topic="CLIENT_CREATE"):
        """Make a webhook request with proper signature"""
        payload = json.dumps({
            "topic": topic,
            "itemId": "test_id_123",
            **payload_data
        })

        signature = self._generate_signature(payload)

        return self.client.post(
            '/jobber/webhooks',
            data=payload,
            content_type='application/json',
            headers={'X-Jobber-Signature': f'sha256={signature}'}
        )

    def test_webhook_signature_verification_valid(self):
        """Test that valid signatures are accepted"""
        with patch('routes.webhooks.handle_jobber_client_created'):
            response = self._make_webhook_request({})
            self.assertEqual(response.status_code, 200)

    def test_webhook_signature_verification_invalid(self):
        """Test that invalid signatures are rejected"""
        payload = json.dumps({"topic": "CLIENT_CREATE", "itemId": "test_id"})

        response = self.client.post(
            '/jobber/webhooks',
            data=payload,
            content_type='application/json',
            headers={'X-Jobber-Signature': 'invalid_signature'}
        )

        self.assertEqual(response.status_code, 401)

    def test_webhook_signature_verification_missing_header(self):
        """Test that missing signature header is rejected"""
        payload = json.dumps({"topic": "CLIENT_CREATE", "itemId": "test_id"})

        response = self.client.post(
            '/jobber/webhooks',
            data=payload,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)

    @patch('routes.webhooks.JobberAPIClient')
    @patch('routes.webhooks.transform_jobber_client_to_model')
    def test_client_created_webhook(self, mock_transform, mock_api_client):
        """Test client created webhook handler"""
        # Mock API client and transformation
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        mock_client_instance.get_client.return_value = {"id": "test_client"}

        mock_transform.return_value = {
            "jobber_client_id": "test_client_123",
            "company_name": "Test Company",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@testcompany.com"
        }

        # Make webhook request
        response = self._make_webhook_request({}, "CLIENT_CREATE")

        # Verify response
        self.assertEqual(response.status_code, 200)
        mock_client_instance.get_client.assert_called_once_with("test_id_123")
        mock_transform.assert_called_once()

    @patch('routes.webhooks.JobberAPIClient')
    @patch('routes.webhooks.transform_jobber_job_to_model')
    def test_job_created_webhook(self, mock_transform, mock_api_client):
        """Test job created webhook handler"""
        # Mock API client and transformation
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        mock_client_instance.get_job.return_value = {"id": "test_job"}

        mock_transform.return_value = {
            "jobber_job_id": "test_job_123",
            "client_id": "test_client_123",
            "title": "Test Job",
            "status": "scheduled"
        }

        # Make webhook request
        response = self._make_webhook_request({}, "JOB_CREATE")

        # Verify response
        self.assertEqual(response.status_code, 200)
        mock_client_instance.get_job.assert_called_once_with("test_id_123")
        mock_transform.assert_called_once()

    @patch('routes.webhooks.JobberAPIClient')
    @patch('routes.webhooks.transform_jobber_invoice_to_model')
    def test_invoice_created_webhook(self, mock_transform, mock_api_client):
        """Test invoice created webhook handler"""
        # Mock API client and transformation
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        mock_client_instance.get_invoice.return_value = {"id": "test_invoice"}

        mock_transform.return_value = {
            "jobber_invoice_id": "test_invoice_123",
            "client_id": "test_client_123",
            "invoice_number": "INV-001",
            "status": "sent",
            "total_amount": 150.00
        }

        # Make webhook request
        response = self._make_webhook_request({}, "INVOICE_CREATE")

        # Verify response
        self.assertEqual(response.status_code, 200)
        mock_client_instance.get_invoice.assert_called_once_with("test_id_123")
        mock_transform.assert_called_once()

    def test_unknown_webhook_topic(self):
        """Test handling of unknown webhook topics"""
        response = self._make_webhook_request({}, "UNKNOWN_TOPIC")

        # Should still return 200 but log warning
        self.assertEqual(response.status_code, 200)

    def test_webhook_missing_topic(self):
        """Test webhook request without topic field"""
        payload = json.dumps({"itemId": "test_id_123"})
        signature = self._generate_signature(payload)

        response = self.client.post(
            '/jobber/webhooks',
            data=payload,
            content_type='application/json',
            headers={'X-Jobber-Signature': f'sha256={signature}'}
        )

        self.assertEqual(response.status_code, 200)

    def test_webhook_missing_json_body(self):
        """Test webhook request without JSON body"""
        response = self.client.post(
            '/jobber/webhooks',
            content_type='application/json',
            headers={'X-Jobber-Signature': 'test'}
        )

        self.assertEqual(response.status_code, 400)

    @patch('routes.webhooks.JobberAPIClient')
    def test_webhook_api_client_error(self, mock_api_client):
        """Test webhook handling when API client fails"""
        # Mock API client to raise exception
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        mock_client_instance.get_client.side_effect = Exception("API Error")

        # Make webhook request
        response = self._make_webhook_request({}, "CLIENT_CREATE")

        # Should return 200 even on error (webhook best practice)
        self.assertEqual(response.status_code, 200)


class TestJobberModelsUpsert(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app(testing=True)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()

    @patch('models.jobber_models.db')
    def test_jobber_client_upsert_create(self, mock_db):
        """Test JobberClient.upsert creates new client"""
        # Mock query to return None (client doesn't exist)
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        JobberClient.query = mock_query

        # Test upsert
        result = JobberClient.upsert(
            "client_123",
            company_name="Test Company",
            email="test@company.com"
        )

        # Verify new client was created
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('models.jobber_models.db')
    def test_jobber_client_upsert_update(self, mock_db):
        """Test JobberClient.upsert updates existing client"""
        # Mock existing client
        existing_client = MagicMock()
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = existing_client
        JobberClient.query = mock_query

        # Test upsert
        result = JobberClient.upsert(
            "client_123",
            company_name="Updated Company",
            email="updated@company.com"
        )

        # Verify existing client was updated
        self.assertEqual(existing_client.company_name, "Updated Company")
        self.assertEqual(existing_client.email, "updated@company.com")
        mock_db.session.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()