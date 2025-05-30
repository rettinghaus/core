"""
Validating a workspace.
"""
import re
from traceback import format_exc
from pathlib import Path

from ocrd_utils import getLogger, MIMETYPE_PAGE, pushd_popd, is_local_filename, DEFAULT_METS_BASENAME
from ocrd_models import ValidationReport
from ocrd_models.constants import PAGE_ALTIMG_FEATURES
from ocrd_modelfactory import page_from_file

from .constants import FILE_GROUP_CATEGORIES, FILE_GROUP_PREFIX
from .page_validator import PageValidator
from .xsd_page_validator import XsdPageValidator
from .xsd_mets_validator import XsdMetsValidator

#
# -------------------------------------------------
#

class WorkspaceValidator():
    """
    Validator for `OcrdMets <../ocrd_models/ocrd_models.ocrd_mets.html>`.
    """

    @staticmethod
    def check_file_grp(workspace, input_file_grp=None, output_file_grp=None, page_id=None, report=None):
        """
        Return a report on whether input_file_grp is/are in workspace.mets and output_file_grp is/are not.
        To be run before processing

        Arguments:
            workspacec (Workspace) the workspace to validate
            input_file_grp (list|string)  list or comma-separated list of input file groups
            output_file_grp (list|string) list or comma-separated list of output file groups
            page_id (list|string) list or comma-separated list of page_ids to write to
        """
        if not report:
            report = ValidationReport()
        if isinstance(input_file_grp, str):
            input_file_grp = input_file_grp.split(',') if input_file_grp else []
        if isinstance(output_file_grp, str):
            output_file_grp = output_file_grp.split(',') if output_file_grp else []
        if page_id and isinstance(page_id, str):
            page_id = page_id.split(',')

        log = getLogger('ocrd.workspace_validator')
        log.debug("input_file_grp=%s output_file_grp=%s" % (input_file_grp, output_file_grp))
        if input_file_grp:
            for grp in input_file_grp:
                if grp not in workspace.mets.file_groups:
                    report.add_error("Input fileGrp[@USE='%s'] not in METS!" % grp)
        if output_file_grp:
            for grp in output_file_grp:
                if grp in workspace.mets.file_groups:
                    if page_id:
                        for one_page_id in page_id:
                            if next(workspace.mets.find_files(fileGrp=grp, pageId=one_page_id), None):
                                report.add_error("Output fileGrp[@USE='%s'] already contains output for page %s" % (grp, one_page_id))
                    else:
                        report.add_error("Output fileGrp[@USE='%s'] already in METS!" % grp)
        return report

    def __init__(self, resolver, mets_url, src_dir=None, skip=None, download=False,
                 page_strictness='strict', page_coordinate_consistency='poly',
                 include_fileGrp=None, exclude_fileGrp=None
                 ):
        """
        Construct a new WorkspaceValidator.

        Args:
            resolver (Resolver):
            mets_url (string):
            src_dir (string):
            skip (list):
            download (boolean):
            page_strictness ("strict"|"lax"|"fix"|"off"): how strict to check
                multi-level TextEquiv consistency of PAGE XML files
            page_coordinate_consistency ("poly"|"baseline"|"both"|"off"): check whether each
                segment's coords are fully contained within its parent's:
                 * `"poly"`: *Region/TextLine/Word/Glyph in Border/*Region/TextLine/Word
                 * `"baseline"`: Baseline in TextLine
                 * `"both"`: both `poly` and `baseline` checks
                 * `"off"`: no coordinate checks
            include_fileGrp (list[str]): filegrp whitelist
            exclude_fileGrp (list[str]): filegrp blacklist
        """
        self.report = ValidationReport()
        self.skip = skip if skip else []
        self.log = getLogger('ocrd.workspace_validator')
        self.log.debug('resolver=%s mets_url=%s src_dir=%s', resolver, mets_url, src_dir)
        self.resolver = resolver
        if mets_url is None and src_dir is not None:
            mets_url = f'{src_dir}/{DEFAULT_METS_BASENAME}'
        self.mets_url = mets_url
        self.download = download
        self.page_strictness = page_strictness
        self.page_coordinate_consistency = page_coordinate_consistency
        # there will be more options to come
        self.page_checks = [check for check in ['mets_fileid_page_pcgtsid',
                                                'imagefilename',
                                                'alternativeimage_filename',
                                                'alternativeimage_comments',
                                                'dimension',
                                                'page',
                                                'page_xsd']
                            if check not in self.skip]

        self.find_kwargs = {"include_fileGrp": include_fileGrp, "exclude_fileGrp": exclude_fileGrp}
        self.src_dir = src_dir
        self.workspace = None
        self.mets = None

    @staticmethod
    def validate(*args, **kwargs):
        """
        Validates the workspace of a METS URL against the specs

        Arguments:
            resolver (:class:`ocrd.Resolver`): Resolver
            mets_url (string): URL of the METS file
            src_dir (string, None): Directory containing mets file
            skip (list): Validation checks to omit. One or more of 
                'mets_unique_identifier',
                'mets_files', 'pixel_density', 'dimension', 'url',
                'multipage', 'page', 'page_xsd', 'mets_xsd', 
                'mets_fileid_page_pcgtsid'
            download (boolean): Whether to download remote file references
                temporarily during validation (like a processor would)

        Returns:
            report (:class:`ValidationReport`) Report on the validity
        """
        validator = WorkspaceValidator(*args, **kwargs)
        return validator._validate() # pylint: disable=protected-access

    def _validate(self):
        """
        Actual validation.
        """
        try:
            self._resolve_workspace()
        except Exception as e: # pylint: disable=broad-except
            self.log.warning("Failed to instantiate workspace: %s", e)
            self.report.add_error(f"Failed to instantiate workspace: {e}")
            return self.report
        with pushd_popd(self.workspace.directory):
            try:
                if 'mets_unique_identifier' not in self.skip:
                    self._validate_mets_unique_identifier()
                if 'mets_files' not in self.skip:
                    self._validate_mets_files()
                if 'pixel_density' not in self.skip:
                    self._validate_pixel_density()
                if 'multipage' not in self.skip:
                    self._validate_multipage()
                if 'mets_xsd' not in self.skip:
                    self._validate_mets_xsd()
                if self.page_checks:
                    self._validate_page()
            except Exception: # pylint: disable=broad-except
                self.report.add_error(f"Validation aborted with exception: {format_exc()}")
        return self.report

    def _resolve_workspace(self):
        """
        Clone workspace from mets_url unless workspace was provided.
        """
        self.log.debug('_resolve_workspace')
        if self.workspace is None:
            self.workspace = self.resolver.workspace_from_url(self.mets_url, src_baseurl=self.src_dir)
            self.mets = self.workspace.mets

    def _validate_mets_unique_identifier(self):
        """
        Validate METS unique identifier exists.

        See `spec <https://ocr-d.github.io/mets#unique-id-for-the-document-processed>`_.
        """
        self.log.debug('_validate_mets_unique_identifier')
        if self.mets.unique_identifier is None:
            self.report.add_error("METS has no unique identifier")

    def _validate_imagefilename(self):
        """
        Validate that the imageFilename is correctly set to a filename relative to the workspace
        """
        self.log.debug('_validate_imagefilename')
        for f in self.mets.find_files(mimetype=MIMETYPE_PAGE, **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            page = page_from_file(f).get_Page()
            imageFilename = page.imageFilename
            if is_local_filename(imageFilename):
                kwargs = dict(local_filename=imageFilename, **self.find_kwargs)
            else:
                kwargs = dict(url=imageFilename, **self.find_kwargs)
            if not self.mets.find_files(**kwargs):
                self.report.add_error(f"PAGE '{f.ID}': imageFilename '{imageFilename}' not found in METS")
            if is_local_filename(imageFilename) and not Path(imageFilename).exists():
                self.report.add_warning(f"PAGE '{f.ID}': imageFilename '{imageFilename}' points to non-existent local file")

    def _validate_dimension(self):
        """
        Validate image height and PAGE imageHeight match
        """
        self.log.info('_validate_dimension')
        for f in self.mets.find_files(mimetype=MIMETYPE_PAGE, **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            page = page_from_file(f).get_Page()
            _, _, exif = self.workspace.image_from_page(page, f.pageId)
            if page.imageHeight != exif.height:
                self.report.add_error(f"PAGE '{f.ID}': @imageHeight != image's actual height ({page.imageHeight} != {exif.height})")
            if page.imageWidth != exif.width:
                self.report.add_error(f"PAGE '{f.ID}': @imageWidth != image's actual width ({page.imageWidth} != {exif.width})")

    def _validate_multipage(self):
        """
        Validate the number of images per file is 1 (TIFF allows multi-page images)

        See `spec <https://ocr-d.github.io/mets#no-multi-page-images>`_.
        """
        self.log.debug('_validate_multipage')
        for f in self.mets.find_files(mimetype='//image/.*', **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            try:
                exif = self.workspace.resolve_image_exif(f.local_filename)
                if exif.n_frames > 1:
                    self.report.add_error(f"Image '{f.ID}': More than 1 frame: {exif.n_frames}")
            except FileNotFoundError:
                self.report.add_error(f"Image '{f.ID}': Could not retrieve (local_filename='{f.local_filename}', url='{f.url}')")
                return

    def _validate_pixel_density(self):
        """
        Validate image pixel density

        See `spec <https://ocr-d.github.io/mets#pixel-density-of-images-must-be-explicit-and-high-enough>`_.
        """
        self.log.debug('_validate_pixel_density')
        for f in self.mets.find_files(mimetype='//image/.*', **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            exif = self.workspace.resolve_image_exif(f.local_filename)
            for k in ['xResolution', 'yResolution']:
                v = exif.__dict__.get(k)
                if v is None or v <= 72:
                    self.report.add_notice(f"Image '{f.ID}': {k} ({v} pixels per {exif.resolutionUnit}) is suspiciously low")

    def _validate_mets_file_group_names(self):
        """
        Ensure ``USE`` attributes of ``mets:fileGrp`` conform to OCR-D naming schema..

        See `spec <https://ocr-d.github.io/mets#file-group-use-syntax>`_.
        """
        self.log.debug('_validate_mets_file_group_names')
        for fileGrp in self.mets.file_groups:
            if not fileGrp.startswith(FILE_GROUP_PREFIX):
                self.report.add_notice(f"fileGrp USE '{fileGrp}' does not begin with '{FILE_GROUP_PREFIX}'")
            else:
                # OCR-D-FOO-BAR -> ('FOO', 'BAR')
                # \____/\_/ \_/
                #   |    |   |
                # Prefix |  Name
                #     Category
                category = fileGrp[len(FILE_GROUP_PREFIX):]
                name = None
                if '-' in category:
                    category, name = category.split('-', 1)
                if category not in FILE_GROUP_CATEGORIES:
                    self.report.add_notice(f"Unspecified USE category '{category}' in fileGrp '{fileGrp}'")
                if name is not None and not re.match(r'^[A-Z0-9-]{3,}$', name):
                    self.report.add_notice(f"Invalid USE name '{name}' in fileGrp '{fileGrp}'")

    def _validate_mets_files(self):
        """
        Validate ``mets:file`` URLs are sane.
        """
        self.log.debug('_validate_mets_files')
        try:
            next(self.mets.find_files(**self.find_kwargs))
        except StopIteration:
            self.report.add_error("No files")
        for f in self.mets.find_files(**self.find_kwargs):
            if f._el.get('GROUPID'): # pylint: disable=protected-access
                self.report.add_notice(f"File '{f.ID}' has GROUPID attribute - document might need an update")
            if not (f.url or f.local_filename):
                self.report.add_error(f"File '{f.ID}' has neither mets:Flocat[@LOCTYPE='URL']/@xlink:href nor mets:FLocat[@LOCTYPE='OTHER'][@OTHERLOCTYPE='FILE']/xlink:href")
                continue
            if f.url and 'url' not in self.skip:
                if re.match(r'^file:/[^/]', f.url):
                    self.report.add_error(f"File '{f.ID}' has an invalid (Java-specific) file URL '{f.url}'")
                elif ':' not in f.url:
                    self.report.add_error(f"File '{f.ID}' has an invalid (non-URI) file URL '{f.url}'")
                    continue
                scheme = f.url[0:f.url.index(':')]
                if scheme not in ('http', 'https', 'file'):
                    self.report.add_warning(f"File '{f.ID}' has non-HTTP, non-file URL '{f.url}'")

    def _validate_page(self):
        """
        Run PageValidator on the PAGE-XML documents referenced in the METS.
        """
        self.log.debug('_validate_page')
        for f in self.mets.find_files(mimetype=MIMETYPE_PAGE, **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            if 'page_xsd' in self.page_checks:
                for err in XsdPageValidator.validate(Path(f.local_filename)).errors:
                    self.report.add_error("%s: %s" % (f.ID, err))
            if 'page' in self.page_checks:
                page_report = PageValidator.validate(ocrd_file=f,
                                                     page_textequiv_consistency=self.page_strictness,
                                                     check_coords=self.page_coordinate_consistency in ['poly', 'both'],
                                                     check_baseline=self.page_coordinate_consistency in ['baseline', 'both'])
                self.report.merge_report(page_report)
            pcgts = page_from_file(f)
            page = pcgts.get_Page()
            if 'dimension' in self.page_checks:
                img = self.workspace._resolve_image_as_pil(page.imageFilename)
                if page.imageHeight != img.height:
                    self.report.add_error(f"PAGE '{f.ID}': @imageHeight != image's actual height ({page.imageHeight} != {img.height})")
                if page.imageWidth != img.width:
                    self.report.add_error(f"PAGE '{f.ID}': @imageWidth != image's actual width ({page.imageWidth} != {img.width})")
            if 'imagefilename' in self.page_checks:
                imageFilename = page.imageFilename
                if is_local_filename(imageFilename):
                    kwargs = dict(local_filename=imageFilename, **self.find_kwargs)
                else:
                    kwargs = dict(url=imageFilename, **self.find_kwargs)
                if not self.mets.find_files(**kwargs):
                    self.report.add_error(f"PAGE '{f.ID}': imageFilename '{imageFilename}' not found in METS")
                if is_local_filename(imageFilename) and not Path(imageFilename).exists():
                    self.report.add_warning(f"PAGE '{f.ID}': imageFilename '{imageFilename}' points to non-existent local file")
            if 'alternativeimage_filename' in self.page_checks:
                for altimg in page.get_AllAlternativeImages():
                    if is_local_filename(altimg.filename):
                        kwargs = dict(local_filename=altimg.filename, **self.find_kwargs)
                    else:
                        kwargs = dict(url=altimg.filename, **self.find_kwargs)
                    if not self.mets.find_files(**kwargs):
                        self.report.add_error(f"PAGE '{f.ID}': {altimg.parent_object_.id} AlternativeImage "
                                              f"'{altimg.filename}' not found in METS")
                    if is_local_filename(altimg.filename) and not Path(altimg.filename).exists():
                        self.report.add_warning(f"PAGE '{f.ID}': {altimg.parent_object_.id} AlternativeImage "
                                                f"'{altimg.filename}' points to non-existent local file")
            if 'alternativeimage_comments' in self.page_checks:
                for altimg in page.get_AllAlternativeImages():
                    if altimg.comments is None:
                        self.report.add_error(f"PAGE '{f.ID}': {altimg.parent_object_.id} AlternativeImage "
                                              f"'{altimg.filename}' features not specified in PAGE")
                    else:
                        for feature in altimg.comments.split(','):
                            if feature not in PAGE_ALTIMG_FEATURES:
                                self.report.add_error(f"PAGE '{f.ID}': {altimg.parent_object_.id} AlternativeImage "
                                                      f"'{altimg.filename}' feature '{feature}' not standardized for PAGE")
            if 'mets_fileid_page_pcgtsid' in self.page_checks and pcgts.pcGtsId != f.ID:
                self.report.add_warning('pc:PcGts/@pcGtsId differs from mets:file/@ID: "%s" !== "%s"' % (pcgts.pcGtsId or '', f.ID or ''))


    def _validate_page_xsd(self):
        """
        Validate all PAGE-XML files against PAGE XSD schema
        """
        self.log.debug('_validate_page_xsd')
        for f in self.mets.find_files(mimetype=MIMETYPE_PAGE, **self.find_kwargs):
            if not f.local_filename and not self.download:
                self.log.warning("Not available locally and 'download' is not set: %s", f)
                continue
            self.workspace.download_file(f)
            for err in XsdPageValidator.validate(Path(f.local_filename)).errors:
                self.report.add_error("%s: %s" % (f.ID, err))
        self.log.debug("Finished validating all PAGE-XML files against XSD")

    def _validate_mets_xsd(self):
        """
        Validate METS against METS XSD schema
        """
        self.log.debug('_validate_mets_xsd')
        self.log.debug("Validating METS %s against XSD" % self.workspace.mets_target)
        for err in XsdMetsValidator.validate(Path(self.workspace.mets_target)).errors:
            self.report.add_error("%s: %s" % (self.workspace.mets_target, err))
        self.log.debug("Finished Validating METS against XSD")
