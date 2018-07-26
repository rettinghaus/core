from test.base import TestCase, main, assets
from ocrd.model import OcrdExif

# pylint: disable=no-member
class TestOcrdExif(TestCase):

    def test_tiff(self):
        exif = OcrdExif.from_filename(assets.path_to('SBB0000F29300010000/00000001.tif'))
        self.assertEqual(exif.width, 2875)
        self.assertEqual(exif.height, 3749)
        self.assertEqual(exif.xResolution, 300)
        self.assertEqual(exif.yResolution, 300)

    def test_png(self):
        exif = OcrdExif.from_filename(assets.path_to('kant_aufklaerung_1784-binarized/kant_aufklaerung_1784_0020.bin.png'))
        self.assertEqual(exif.width, 1457)
        self.assertEqual(exif.height, 2084)
        self.assertEqual(exif.xResolution, 0)
        self.assertEqual(exif.yResolution, 0)

    def test_jpg(self):
        exif = OcrdExif.from_filename(assets.path_to('leptonica_samples/1555.007.jpg'))
        self.assertEqual(exif.width, 944)
        self.assertEqual(exif.height, 1472)
        self.assertEqual(exif.xResolution, 1)
        self.assertEqual(exif.yResolution, 1)

    def test_jp2(self):
        exif = OcrdExif.from_filename(assets.path_to('kant_aufklaerung_1784-jp2/kant_aufklaerung_1784_0020.jp2'))
        self.assertEqual(exif.width, 1457)
        self.assertEqual(exif.height, 2084)
        #  self.assertEqual(exif.xResolution, 1)
        #  self.assertEqual(exif.yResolution, 1)

if __name__ == '__main__':
    main()
