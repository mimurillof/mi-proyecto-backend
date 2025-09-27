import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.report_normalizer import (
    normalize_report_for_schema,
    ensure_image_sources,
    ReportValidationError,
)


class ReportNormalizerTests(unittest.TestCase):
    def test_normalize_report_removes_null_fields(self):
        raw_report = {
            "fileName": "informe.pdf",
            "document": {
                "title": "Titulo",
                "author": "Autor",
                "subject": "Asunto",
                "extra": "se descarta",
            },
            "content": [
                {
                    "type": "header1",
                    "text": "Encabezado",
                    "style": None,
                    "height": None,
                    "path": None,
                    "caption": None,
                    "width": None,
                    "headers": None,
                    "rows": None,
                    "items": None,
                    "supabase": None,
                    "otro": "valor",
                },
                {
                    "type": "table",
                    "headers": ["Col1", "Col2", None],
                    "rows": [["a", "b"], "fila_invalida"],
                    "items": [
                        {"key": "K", "value": None},
                        None,
                        ["x", None, "y"],
                    ],
                },
            ],
            "metadata": "no permitido",
        }

        normalized = normalize_report_for_schema(raw_report)

        self.assertEqual(set(normalized.keys()), {"fileName", "document", "content"})
        self.assertEqual(normalized["fileName"], "informe.pdf")
        self.assertEqual(
            normalized["document"],
            {
                "title": "Titulo",
                "author": "Autor",
                "subject": "Asunto",
            },
        )

        header_block = normalized["content"][0]
        self.assertEqual(header_block, {"type": "header1", "text": "Encabezado"})

        table_block = normalized["content"][1]
        self.assertEqual(table_block["headers"], ["Col1", "Col2"])
        self.assertEqual(table_block["rows"], [["a", "b"]])
        self.assertEqual(table_block["items"], [{"key": "K"}, ["x", "y"]])

    def test_image_dimensions_are_capped(self):
        raw_report = {
            "fileName": "informe.pdf",
            "content": [
                {
                    "type": "image",
                    "path": "huge.png",
                    "width": 5000,
                    "height": 8000,
                    "headers": ["H1"],
                    "rows": [["R1"]],
                    "items": ["unused"],
                }
            ],
        }

        normalized = normalize_report_for_schema(raw_report)
        enhanced = ensure_image_sources(normalized, bucket="portfolio-files", prefix="Graficos")
        image_block = enhanced["content"][0]

        self.assertLessEqual(image_block["width"], 10.0)
        self.assertLessEqual(image_block["height"], 10.0)
        expected_height = image_block["width"] * (9.0 / 16.0)
        self.assertAlmostEqual(image_block["height"], expected_height, places=4)
        self.assertNotIn("headers", image_block)
        self.assertNotIn("rows", image_block)
        self.assertNotIn("items", image_block)

    def test_ensure_image_sources_populates_supabase_metadata(self):
        raw_report = {
            "fileName": "informe.pdf",
            "content": [
                {
                    "type": "image",
                    "path": "carpeta/imagen.png",
                    "width": 640,
                },
                {
                    "type": "paragraph",
                    "text": "Contenido",
                },
            ],
        }

        normalized = normalize_report_for_schema(raw_report)
        enhanced = ensure_image_sources(
            normalized,
            bucket="portfolio-files",
            prefix="Graficos",
            transform_width=800,
        )

        image_block = enhanced["content"][0]
        supabase_data = image_block.get("supabase")

        self.assertIsInstance(supabase_data, dict)
        self.assertEqual(supabase_data["bucket"], "portfolio-files")
        self.assertEqual(supabase_data["path"], "Graficos/carpeta/imagen.png")
        self.assertEqual(supabase_data["transform"]["width"], 800)
        self.assertEqual(supabase_data["transform"]["resize"], "contain")

    def test_normalize_report_requires_mandatory_fields(self):
        with self.assertRaises(ReportValidationError):
            normalize_report_for_schema({"content": []})

        with self.assertRaises(ReportValidationError):
            normalize_report_for_schema({"fileName": "a.pdf"})


if __name__ == "__main__":
    unittest.main()
