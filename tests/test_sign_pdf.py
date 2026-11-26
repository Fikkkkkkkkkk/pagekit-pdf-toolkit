"""Focused visual signature endpoint checks."""

import io
import json
import sys
import unittest
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app import create_app


class SignPdfTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        writer = PdfWriter()
        writer.add_blank_page(width=400, height=600)
        writer.add_blank_page(width=500, height=700)
        writer.add_outline_item('Second page', 1)
        writer.add_metadata({'/Title': 'Original'})
        self.original = io.BytesIO()
        writer.write(self.original)
        self.pdf = self.original.getvalue()
        image = Image.new('RGBA', (80, 30), (0, 0, 0, 0))
        for x in range(10, 70):
            for y in range(12, 18):
                image.putpixel((x, y), (20, 30, 100, 190))
        output = io.BytesIO()
        image.save(output, format='PNG')
        self.signature = output.getvalue()

    def post(self, placements, pdf=None, signature=None):
        return self.client.post('/api/sign-pdf', data={
            'file': (io.BytesIO(self.pdf if pdf is None else pdf), 'source.pdf'),
            'signature': (io.BytesIO(self.signature if signature is None else signature), 'signature.png'),
            'placements': json.dumps(placements),
        })

    def test_places_transparent_signature_on_selected_pages_only(self):
        response = self.post([{'page': 2, 'x': .25, 'y': .6, 'width': .4, 'height': .1}])
        self.assertEqual(response.status_code, 200, response.json)
        output = PdfReader(io.BytesIO(response.data))
        self.assertEqual(len(output.pages), 2)
        self.assertEqual(output.metadata.title, 'Original')
        self.assertEqual(len(output.outline), 1)
        self.assertNotIn('/PKSignature', output.pages[0].get('/Resources', {}).get('/XObject', {}))
        image = output.pages[1]['/Resources']['/XObject']['/PKSignature'].get_object()
        self.assertEqual(image['/Width'], 80)
        self.assertIn('/SMask', image)
        self.assertEqual(len(image.get_data()), 80 * 30 * 3)
        self.assertEqual(len(image['/SMask'].get_object().get_data()), 80 * 30)
        self.assertEqual(self.pdf, self.original.getvalue())

    def test_rejects_invalid_input(self):
        placement = {'page': 1, 'x': .8, 'y': .8, 'width': .4, 'height': .1}
        self.assertIn('outside', self.post([placement]).json['error'])
        self.assertIn('cannot be read', self.post([{'page': 1, 'x': 0, 'y': 0, 'width': .2, 'height': .1}], pdf=b'%PDF-broken').json['error'])
        self.assertIn('cannot be read', self.post([{'page': 1, 'x': 0, 'y': 0, 'width': .2, 'height': .1}], signature=b'\x89PNG\r\n\x1a\ninvalid').json['error'])

    def test_keeps_a_different_angle_on_each_page(self):
        response = self.post([
            {'page': 1, 'x': .35, 'y': .4, 'width': .3, 'height': .1, 'angle': 45},
            {'page': 2, 'x': .35, 'y': .4, 'width': .3, 'height': .1, 'angle': -30},
        ])
        self.assertEqual(response.status_code, 200, response.json)
        output = PdfReader(io.BytesIO(response.data))
        first = output.pages[0].get_contents().get_data()
        second = output.pages[1].get_contents().get_data()
        self.assertIn(b'0.70710678 -0.70710678 0.70710678 0.70710678', first)
        self.assertIn(b'0.86602540 0.50000000 -0.50000000 0.86602540', second)

    def test_rejects_rotated_overflow_and_invalid_angle(self):
        placement = {'page': 1, 'x': .7, 'y': .4, 'width': .3, 'height': .2, 'angle': 45}
        self.assertIn('rotated signature outside', self.post([placement]).json['error'])
        placement['angle'] = 181
        self.assertIn('invalid signature angle', self.post([placement]).json['error'])


if __name__ == '__main__':
    unittest.main()
