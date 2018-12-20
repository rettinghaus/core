from test.base import TestCase, assets, main # pylint: disable=import-error,no-name-in-module
from ocrd.resolver import Resolver
from ocrd.validator import PageValidator
from ocrd.model.ocrd_page import parse

class TestPageValidator(TestCase):

    def setUp(self):
        pass

    def test_validate_filename(self):
        report = PageValidator.validate_filename(assets.path_to('glyph-consistency/data/OCR-D-GT-PAGE/FAULTY_GLYPHS'))
        self.assertEqual(len(report.errors), 17, 'errors')

    def test_validate_ocrd_file(self):
        resolver = Resolver()
        workspace = resolver.workspace_from_url(assets.url_of('glyph-consistency/data/mets.xml'))
        ocrd_file = workspace.mets.find_files(ID="FAULTY_GLYPHS_FILE")[0]
        report = PageValidator.validate_ocrd_file(ocrd_file)
        self.assertEqual(len(report.errors), 17, 'errors')

    def test_validate_lax(self):
        resolver = Resolver()
        workspace = resolver.workspace_from_url(assets.url_of('kant_aufklaerung_1784/data/mets.xml'))
        ocrd_file = workspace.mets.find_files(ID="PAGE_0020_PAGE")[0]
        self.assertEqual(len(PageValidator.validate_ocrd_file(ocrd_file).errors), 25, '25 errors - strict')
        self.assertEqual(len(PageValidator.validate_ocrd_file(ocrd_file, strictness='lax').errors), 0, 'no errors - lax')

    def test_fix(self):
        page = parse(assets.path_to('glyph-consistency/data/OCR-D-GT-PAGE/FAULTY_GLYPHS'), silence=True)
        report = PageValidator.validate_ocrd_page(page)
        self.assertEqual(len(report.errors), 17, 'errors')
        PageValidator.validate_ocrd_page(page, strictness='fix')
        report = PageValidator.validate_ocrd_page(page)
        self.assertEqual(len(report.errors), 0, 'no more errors')

if __name__ == '__main__':
    main()