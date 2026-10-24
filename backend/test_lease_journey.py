"""Public-lease retrieval, privacy, and guide APIs; no external network or AI."""
import io
import socket
import time
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import lease_journey as journey


def pdf_bytes(text='RESIDENTIAL LEASE AGREEMENT. Landlord and Tenant agree to monthly rent of $1400.'):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    safe = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream.set_data(('BT /F1 12 Tf 20 700 Td (' + safe + ') Tj ET').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class Response:
    def __init__(self, data, content_type='text/html', status=200):
        self.data = data
        self.headers = {'Content-Type': content_type}
        self.status_code = status
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, size):
        for i in range(0, len(self.data), size):
            yield self.data[i:i + size]


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        journey._CACHE.clear()
        self.row = {'website': 'https://provider.example/', 'source_url': 'https://provider.example/floorplans/one'}

    def test_automatic_public_pdf_is_always_a_reference_and_numbers_are_redacted(self):
        html = b'<a href="/documents/sample-lease.pdf">Sample lease agreement</a>'
        pdf = pdf_bytes('RESIDENTIAL LEASE AGREEMENT. Landlord and Tenant. SSN: 123-45-6789.')
        with patch('lease_journey._public_host', return_value=True), patch('lease_journey.requests.get', side_effect=[Response(html), Response(pdf, 'application/pdf')]) as get:
            result = journey.retrieve_public_document(self.row)
            self.assertEqual(result['status'], 'public_reference')
            self.assertEqual(result['document']['kind'], 'public_reference')
            self.assertEqual(result['document']['source_url'], 'https://provider.example/documents/sample-lease.pdf')
            self.assertNotIn('123-45-6789', result['document']['text'])
            self.assertIn('REDACTED', result['document']['text'])
            for call in get.call_args_list:
                self.assertIs(call.kwargs['allow_redirects'], False)
                self.assertIsInstance(call.kwargs['auth'], journey.PublicDocumentAuth)
            self.assertEqual(journey.retrieve_public_document(self.row), result)
            self.assertEqual(get.call_count, 2)

    def test_application_brochure_and_unrelated_host_never_become_lease(self):
        html = b'<a href="/application-lease.pdf">Lease application</a><a href="/brochure-lease.pdf">Lease brochure</a><a href="https://unrelated.example/lease.pdf">Lease agreement</a>'
        with patch('lease_journey._public_host', return_value=True), patch('lease_journey.requests.get', return_value=Response(html)) as get:
            result = journey.retrieve_public_document(self.row)
            self.assertEqual(result['status'], 'not_found')
            self.assertIsNone(result['document'])
            self.assertEqual(get.call_count, 2)

    def test_provider_failure_is_not_reported_as_no_lease_exists(self):
        with patch('lease_journey._download', side_effect=journey.ProviderUnavailable('offline')):
            result = journey.retrieve_public_document(self.row)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['checked_urls'], [])
        self.assertIn('couldn’t complete', result['message'])

    def test_agency_directory_is_not_scanned_as_a_provider(self):
        row = dict(source_kind='public_authority', source_url='https://county.example/directory.pdf', website=None)
        with patch('lease_journey._download') as download:
            result = journey.retrieve_public_document(row)
        download.assert_not_called()
        self.assertIsNone(result['document'])
        self.assertIn('agency directory', result['message'])
        with patch('lease_journey._download') as download:
            result = journey.retrieve_public_document(dict(row, source_kind='official_directory', website=row['source_url']))
        download.assert_not_called()
        self.assertIsNone(result['document'])
        row['website'] = 'https://provider.example/'
        with patch('lease_journey._download', return_value=(b'<p>Call leasing</p>', 'text/html')) as download:
            journey.retrieve_public_document(row)
        self.assertEqual(download.call_count, 1)
        self.assertEqual(download.call_args.args[0], row['website'])

    def test_redirect_and_oversized_responses_are_rejected(self):
        with patch('lease_journey._public_host', return_value=True), patch('lease_journey.requests.get', return_value=Response(b'', status=302)):
            with self.assertRaises(journey.ProviderUnavailable):
                journey._download(self.row['website'], {'provider.example'}, 100, time.monotonic() + 10)
        with patch('lease_journey._public_host', return_value=True), patch('lease_journey.requests.get', return_value=Response(b'x' * 200)):
            with self.assertRaises(journey.ProviderUnavailable):
                journey._download(self.row['website'], {'provider.example'}, 100, time.monotonic() + 10)

    def test_local_hosts_credentials_and_non_https_are_rejected(self):
        for url in ['http://provider.example/a', 'https://provider.example:8443/a', 'https://user:secret@provider.example/a', 'https://127.0.0.1/lease.pdf']:
            self.assertFalse(journey._allowed_url(url, {'provider.example'}), url)
        with patch('lease_journey.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
            self.assertFalse(journey._public_host('provider.example'))
        with patch('lease_journey.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]):
            self.assertTrue(journey._public_host('provider.example'))
        with patch('lease_journey._public_host', return_value=False), patch('lease_journey.requests.get') as get:
            with self.assertRaises(journey.ProviderUnavailable):
                journey._download(self.row['website'], {'provider.example'}, 100, time.monotonic() + 10)
            get.assert_not_called()

    def test_nonlease_unreadable_and_long_pdfs_are_not_silently_loaded(self):
        for document in [b'<html>Log in</html>', pdf_bytes('Apartment brochure and amenities.')]:
            with self.assertRaises(journey.ProviderUnavailable): journey._pdf_text(document)
        with patch('lease_journey.PdfReader', return_value=SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda: 'x' * (journey.MAX_TEXT_CHARS + 1))])):
            with self.assertRaisesRegex(journey.ProviderUnavailable, 'too long'):
                journey._pdf_text(b'%PDF-test')
        with patch('lease_journey.PdfReader', return_value=SimpleNamespace(is_encrypted=True)):
            with self.assertRaises(journey.ProviderUnavailable): journey._pdf_text(b'%PDF-test')


class LeaseApiTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.client = app.test_client()

    def test_context_is_fast_without_provider_network_and_preserves_exact_plan(self):
        with patch('lease_journey.retrieve_public_document') as retrieve:
            response = self.client.get('/api/listings/arbor-heights-two-bedroom/lease')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['listing']['id'], 'arbor-heights-two-bedroom')
        self.assertEqual(data['listing']['floor_plan'], '2 bedroom')
        self.assertEqual(data['provider_document']['status'], 'not_checked')
        retrieve.assert_not_called()
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get('/api/listings/missing/lease').status_code, 404)
        with self.client.get('/lease') as page:
            self.assertEqual(page.status_code, 200)

    def test_document_check_only_accepts_a_catalog_housing_record(self):
        with patch('lease_journey.retrieve_public_document', return_value={'status': 'not_found', 'document': None, 'message': 'No public document found'}) as retrieve:
            response = self.client.get('/api/listings/virginia-gardens-one-bedroom/lease/document')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(retrieve.call_args.args[0]['id'], 'virginia-gardens-one-bedroom')
        self.assertEqual(self.client.get('/api/listings/missing/lease/document').status_code, 404)

    def test_question_is_grounded_in_submitted_part_and_both_inputs_are_redacted(self):
        with patch('app.answer_lease_question', return_value='This section does not mention an early termination fee.') as answer:
            response = self.client.post('/api/lease/question', json={'text': 'Rent $1400. SSN: 123-45-6789', 'question': 'My account 12345678: what is the notice period?'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('123-45-6789', answer.call_args.args[0])
        self.assertNotIn('12345678', answer.call_args.args[1])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_question_validation_and_failure_keep_other_parts_unanswered(self):
        for body in [[], {}, {'text': [], 'question': 'why?'}, {'text': 'x' * 15001, 'question': 'why?'}, {'text': 'rent', 'question': 'x' * 1501}, {'text': 'rent', 'question': ''}]:
            self.assertEqual(self.client.post('/api/lease/question', json=body).status_code, 400)
        with patch('app.answer_lease_question', side_effect=RuntimeError('private internal details')):
            response = self.client.post('/api/lease/question', json={'text': 'rent', 'question': 'why?'})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private internal details', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_explanation_still_uses_existing_service_and_is_not_cached(self):
        with patch('app.explain_lease', return_value='SUMMARY: informational explanation.') as explain:
            response = self.client.post('/api/lease', json={'text': 'Rent is $1400. SSN: 123-45-6789.'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('123-45-6789', explain.call_args.args[0])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')



if __name__ == '__main__':
    unittest.main()
