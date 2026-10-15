
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from preview_block import extract_block, main, render


class ExtractBlockTests(unittest.TestCase):
    def test_cursor_on_body_or_fences(self):
        text = "Heading\n```puml\nAlice -> Bob: Привет\n```\nAfter"
        for row in (2, 3, 4):
            self.assertEqual(extract_block(text, row), ("Alice -> Bob: Привет", 2))

    def test_multiple_blocks_and_tilde_fence(self):
        text = "```python\nprint(1)\n```\n~~~plantuml\nA -> B\n~~~\n```puml\nC -> D\n```"
        self.assertEqual(extract_block(text, 5), ("A -> B", 4))
        self.assertEqual(extract_block(text, 8), ("C -> D", 7))

    def test_nested_example_is_not_a_diagram(self):
        text = "````markdown\n```puml\nA -> B\n```\n````"
        with self.assertRaisesRegex(ValueError, "language"):
            extract_block(text, 3)

    def test_shorter_fence_does_not_close_block(self):
        self.assertEqual(extract_block("````puml\n```\nA -> B\n````", 3), ("```\nA -> B", 1))

    def test_crlf_and_indentation(self):
        self.assertEqual(extract_block("  ```PlantUML\r\n  A -> B\r\n  ```\r\n", 2), ("A -> B", 1))

    def test_invalid_locations(self):
        cases = [
            ("text", 1, "Place the cursor"),
            ("```puml\nA -> B", 2, "no closing"),
            ("```puml\n\n```", 2, "empty"),
            ("```python\npass\n```", 2, "language"),
            ("text", 0, "outside"),
            ("text", 2, "outside"),
        ]
        for text, row, message in cases:
            with self.subTest(text=text, row=row), self.assertRaisesRegex(ValueError, message):
                extract_block(text, row)

    def test_failed_render_never_opens_viewer(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "test.md"
            document.write_text("```puml\nA -> B\n```", encoding="utf-8")
            with patch("preview_block.render", side_effect=ValueError("syntax error")), patch("preview_block.subprocess.run") as run:
                self.assertEqual(main([str(document), "2"]), 1)
                run.assert_not_called()


class RealRendererTests(unittest.TestCase):
    def assert_rendered(self, source, document):
        output = render(source, document, 1)
        try:
            self.assertEqual(output, document.parent / "_puml_render.png")
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        finally:
            output.unlink()

    def test_bare_body_with_cyrillic_and_space_in_path(self):
        with tempfile.TemporaryDirectory(prefix="plantuml test ") as directory:
            self.assert_rendered("Alice -> Bob: Привет", Path(directory) / "заметки test.md")

    def test_full_diagram_and_relative_include(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "test.md"
            (document.parent / "participants.puml").write_text("participant Alice\nparticipant Bob\n", encoding="utf-8")
            self.assert_rendered("@startuml\n!include participants.puml\nAlice -> Bob: OK\n@enduml", document)

    def test_invalid_plantuml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "test.md"
            output = render("Alice -> Bob: Previous", document, 1)
            previous = output.read_bytes()
            with self.assertRaisesRegex(ValueError, "could not render"):
                render("@startuml\nthis is not valid diagram syntax !!!!\n@enduml", document, 1)
            self.assertEqual(output.read_bytes(), previous)
            self.assertEqual(list(document.parent.iterdir()), [output])

    def test_successful_render_replaces_single_file(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "test.md"
            output = render("Alice -> Bob: First", document, 1)
            previous = output.read_bytes()
            updated = render("Bob -> Alice: Second", document, 8)
            self.assertEqual(updated, output)
            self.assertNotEqual(updated.read_bytes(), previous)
            self.assertEqual(list(document.parent.iterdir()), [output])

    def test_preview_command(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "test.md"
            document.write_text("```puml\nA -> B\n```", encoding="utf-8")
            output = Path(directory) / "rendered.png"
            with patch("preview_block.render", return_value=output), patch("preview_block.subprocess.run") as run:
                self.assertEqual(main([str(document), "2"]), 0)
                run.assert_called_once_with(["/usr/bin/open", "-a", "Preview", str(output)], check=True, timeout=15)


if __name__ == "__main__":
    unittest.main()
