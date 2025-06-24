"""
Jobber API Client Utilities

Handles authentication and API interactions with the Jobber GraphQL API.
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class JobberAPIClient:
    """Client for interacting with Jobber's GraphQL API"""

    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None):
        self.api_key = api_key or current_app.config.get('JOBBER_API_KEY')
        self.api_secret = api_secret or current_app.config.get('JOBBER_API_SECRET')
        self.base_url = base_url or current_app.config.get('JOBBER_BASE_URL', 'https://api.getjobber.com')
        self.graphql_endpoint = f"{self.base_url}/api/graphql"

        # Rate limiting (2500 requests per 5 minutes)
        self.rate_limit_window = 300  # 5 minutes in seconds
        self.rate_limit_max = 2500
        self.request_times: List[float] = []

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        # Remove requests older than the window
        self.request_times = [t for t in self.request_times if now - t < self.rate_limit_window]

        return len(self.request_times) < self.rate_limit_max

    def _make_request(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a GraphQL request to Jobber API"""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please wait before making more requests.")

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-JOBBER-GRAPHQL-VERSION': '2023-11-15'
        }

        payload = {
            'query': query,
            'variables': variables or {}
        }

        try:
            self.request_times.append(time.time())
            response = requests.post(
                self.graphql_endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if 'errors' in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                raise Exception(f"GraphQL errors: {result['errors']}")

            return result.get('data', {})

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"API request failed: {e}")

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a client by ID from Jobber"""
        query = """
        query GetClient($id: ID!) {
            client(id: $id) {
                id
                firstName
                lastName
                companyName
                emails {
                    address
                    description
                    primary
                }
                phones {
                    number
                    description
                    primary
                }
                billingAddress {
                    street1
                    street2
                    city
                    province
                    postalCode
                    country
                }
                tags {
                    name
                }
                notes {
                    note
                }
                createdAt
                updatedAt
            }
        }
        """

        try:
            result = self._make_request(query, {'id': client_id})
            return result.get('client')
        except Exception as e:
            logger.error(f"Failed to fetch client {client_id}: {e}")
            return None

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a job by ID from Jobber"""
        query = """
        query GetJob($id: ID!) {
            job(id: $id) {
                id
                title
                description
                jobStatus
                startAt
                endAt
                client {
                    id
                }
                jobAddress {
                    street1
                    street2
                    city
                    province
                    postalCode
                    country
                }
                jobNumber
                tags {
                    name
                }
                total {
                    cents
                    currency
                }
                createdAt
                updatedAt
            }
        }
        """

        try:
            result = self._make_request(query, {'id': job_id})
            return result.get('job')
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Fetch an invoice by ID from Jobber"""
        query = """
        query GetInvoice($id: ID!) {
            invoice(id: $id) {
                id
                invoiceNumber
                invoiceStatus
                client {
                    id
                }
                job {
                    id
                }
                subtotal {
                    cents
                    currency
                }
                taxes {
                    cents
                    currency
                }
                total {
                    cents
                    currency
                }
                issuedAt
                dueAt
                sentAt
                paidAt
                lineItems {
                    name
                    description
                    quantity
                    unitCost {
                        cents
                        currency
                    }
                    total {
                        cents
                        currency
                    }
                }
                createdAt
                updatedAt
            }
        }
        """

        try:
            result = self._make_request(query, {'id': invoice_id})
            return result.get('invoice')
        except Exception as e:
            logger.error(f"Failed to fetch invoice {invoice_id}: {e}")
            return None

# Data transformation utilities
def transform_jobber_client_to_model(jobber_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Jobber client data to our model format"""
    primary_email = next((email['address'] for email in jobber_data.get('emails', []) if email.get('primary')), None)
    primary_phone = next((phone['number'] for phone in jobber_data.get('phones', []) if phone.get('primary')), None)

    billing_address = jobber_data.get('billingAddress', {})
    tags = [tag['name'] for tag in jobber_data.get('tags', [])]

    return {
        'jobber_client_id': jobber_data['id'],
        'company_name': jobber_data.get('companyName'),
        'first_name': jobber_data.get('firstName'),
        'last_name': jobber_data.get('lastName'),
        'email': primary_email,
        'phone': primary_phone,
        'address_line1': billing_address.get('street1'),
        'address_line2': billing_address.get('street2'),
        'city': billing_address.get('city'),
        'province': billing_address.get('province'),
        'postal_code': billing_address.get('postalCode'),
        'country': billing_address.get('country'),
        'tags': tags,
        'is_active': True
    }

def transform_jobber_job_to_model(jobber_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Jobber job data to our model format"""
    job_address = jobber_data.get('jobAddress', {})
    tags = [tag['name'] for tag in jobber_data.get('tags', [])]
    total = jobber_data.get('total', {})

    return {
        'jobber_job_id': jobber_data['id'],
        'client_id': jobber_data.get('client', {}).get('id'),
        'title': jobber_data.get('title'),
        'description': jobber_data.get('description'),
        'status': jobber_data.get('jobStatus'),
        'start_date': jobber_data.get('startAt'),
        'end_date': jobber_data.get('endAt'),
        'total_amount': total.get('cents', 0) / 100 if total.get('cents') else None,
        'currency': total.get('currency', 'USD'),
        'job_address_line1': job_address.get('street1'),
        'job_address_line2': job_address.get('street2'),
        'job_city': job_address.get('city'),
        'job_province': job_address.get('province'),
        'job_postal_code': job_address.get('postalCode'),
        'job_country': job_address.get('country'),
        'job_number': jobber_data.get('jobNumber'),
        'tags': tags
    }

def transform_jobber_invoice_to_model(jobber_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Jobber invoice data to our model format"""
    subtotal = jobber_data.get('subtotal', {})
    taxes = jobber_data.get('taxes', {})
    total = jobber_data.get('total', {})

    line_items = []
    for item in jobber_data.get('lineItems', []):
        line_items.append({
            'name': item.get('name'),
            'description': item.get('description'),
            'quantity': item.get('quantity'),
            'unit_cost': item.get('unitCost', {}).get('cents', 0) / 100,
            'total': item.get('total', {}).get('cents', 0) / 100
        })

    return {
        'jobber_invoice_id': jobber_data['id'],
        'client_id': jobber_data.get('client', {}).get('id'),
        'job_id': jobber_data.get('job', {}).get('id'),
        'invoice_number': jobber_data.get('invoiceNumber'),
        'status': jobber_data.get('invoiceStatus'),
        'subtotal': subtotal.get('cents', 0) / 100 if subtotal.get('cents') else None,
        'tax_amount': taxes.get('cents', 0) / 100 if taxes.get('cents') else None,
        'total_amount': total.get('cents', 0) / 100 if total.get('cents') else None,
        'currency': total.get('currency', 'USD'),
        'issue_date': jobber_data.get('issuedAt'),
        'due_date': jobber_data.get('dueAt'),
        'sent_date': jobber_data.get('sentAt'),
        'paid_date': jobber_data.get('paidAt'),
        'line_items': line_items
    }