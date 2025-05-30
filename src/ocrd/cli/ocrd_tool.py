"""
OCR-D CLI: ocrd-tool.json management

.. click:: ocrd.cli.ocrd_tool:ocrd_tool_cli
    :prog: ocrd ocrd-tool
    :nested: full

"""
from inspect import getmodule
from json import dumps
import codecs
import sys
import os
import click

from ocrd.decorators import parameter_option, parameter_override_option
from ocrd.processor import Processor
from ocrd_utils import (
    set_json_key_value_overrides,
    parse_json_string_or_file,
    parse_json_string_with_comments as loads,
    get_moduledir
)
from ocrd_validators import ParameterValidator, OcrdToolValidator

class OcrdToolCtx():

    def __init__(self, filename):
        self.filename = filename
        with codecs.open(filename, encoding='utf-8') as f:
            self.content = f.read()
            # perhaps the validator should _always_ run (for default expansion)
            # so validate command only for the report?
            self.json = loads(self.content)
        self.tool_name = ''

        class BashProcessor(Processor):
            @property
            def metadata(inner_self): # pylint: disable=no-self-argument,arguments-renamed
                return self.json
            @property
            def executable(inner_self): # pylint: disable=no-self-argument,arguments-renamed
                return self.tool_name
            @property
            def moduledir(inner_self): # pylint: disable=no-self-argument,arguments-renamed
                return os.path.dirname(self.filename)
            # set docstrings to empty
            __doc__ = None
            # HACK: override the module-level docstring, too
            getmodule(OcrdToolCtx).__doc__ = None
            def process(inner_self): # pylint: disable=no-self-argument,arguments-renamed
                return super()

        self.processor = BashProcessor

pass_ocrd_tool = click.make_pass_decorator(OcrdToolCtx)

# ----------------------------------------------------------------------
# ocrd ocrd-tool
# ----------------------------------------------------------------------

@click.group('ocrd-tool', help='Work with ocrd-tool.json JSON_FILE')
@click.argument('json_file')
@click.pass_context
def ocrd_tool_cli(ctx, json_file):
    ctx.obj = OcrdToolCtx(json_file)

# ----------------------------------------------------------------------
# ocrd ocrd-tool version
# ----------------------------------------------------------------------

@ocrd_tool_cli.command('version', help='Version of ocrd-tool.json')
@pass_ocrd_tool
def ocrd_tool_version(ctx):
    print(ctx.json['version'])

# ----------------------------------------------------------------------
# ocrd ocrd-tool validate
# ----------------------------------------------------------------------

@ocrd_tool_cli.command('validate', help='Validate an ocrd-tool.json')
@pass_ocrd_tool
def ocrd_tool_validate(ctx):
    report = OcrdToolValidator.validate(ctx.json)
    print(report.to_xml())
    if not report.is_valid:
        return 128

# ----------------------------------------------------------------------
# ocrd ocrd-tool list-tools
# ----------------------------------------------------------------------

@ocrd_tool_cli.command('list-tools', help="List tools")
@pass_ocrd_tool
def ocrd_tool_list(ctx):
    for tool in ctx.json['tools']:
        print(tool)

# ----------------------------------------------------------------------
# ocrd ocrd-tool dump-tools
# ----------------------------------------------------------------------

@ocrd_tool_cli.command('dump-tools', help="Dump tools")
@pass_ocrd_tool
def ocrd_tool_dump(ctx):
    print(dumps(ctx.json['tools'], indent=True))

@ocrd_tool_cli.command('dump-module-dirs', help="Dump module directory of each tool")
@pass_ocrd_tool
def ocrd_tool_dump_module_dirs(ctx):
    print(dumps({tool_name: get_moduledir(tool_name)
                 for tool_name in ctx.json['tools']},
                indent=True))

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool
# ----------------------------------------------------------------------

@ocrd_tool_cli.group('tool', help='Work with a single tool TOOL_NAME')
@click.argument('tool_name')
@pass_ocrd_tool
def ocrd_tool_tool(ctx, tool_name):
    if tool_name not in ctx.json['tools']:
        raise Exception("No such tool: %s" % tool_name)
    ctx.tool_name = tool_name

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool description
# ----------------------------------------------------------------------

@ocrd_tool_tool.command('description', help="Describe tool")
@pass_ocrd_tool
def ocrd_tool_tool_description(ctx):
    print(ctx.json['tools'][ctx.tool_name]['description'])

@ocrd_tool_tool.command('list-resources', help="List tool's file resources")
@pass_ocrd_tool
def ocrd_tool_tool_list_resources(ctx):
    ctx.processor(None).list_resources()

@ocrd_tool_tool.command('resolve-resource', help="Get a tool's file resource full path name")
@click.argument('res_name')
@pass_ocrd_tool
def ocrd_tool_tool_resolve_resource(ctx, res_name):
    print(ctx.processor(None).resolve_resource(res_name))

@ocrd_tool_tool.command('show-resource', help="Dump a tool's file resource")
@click.argument('res_name')
@pass_ocrd_tool
def ocrd_tool_tool_show_resource(ctx, res_name):
    ctx.processor(None).show_resource(res_name)

@ocrd_tool_tool.command('help', help="Generate help for processors")
@click.argument('subcommand', required=False)
@pass_ocrd_tool
def ocrd_tool_tool_params_help(ctx, subcommand):
    ctx.processor(None).show_help(subcommand=subcommand)

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool categories
# ----------------------------------------------------------------------

@ocrd_tool_tool.command('categories', help="Categories of tool")
@pass_ocrd_tool
def ocrd_tool_tool_categories(ctx):
    print('\n'.join(ctx.json['tools'][ctx.tool_name]['categories']))

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool steps
# ----------------------------------------------------------------------

@ocrd_tool_tool.command('steps', help="Steps of tool")
@pass_ocrd_tool
def ocrd_tool_tool_steps(ctx):
    print('\n'.join(ctx.json['tools'][ctx.tool_name]['steps']))

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool dump
# ----------------------------------------------------------------------

@ocrd_tool_tool.command('dump', help="Dump JSON of tool")
@pass_ocrd_tool
def ocrd_tool_tool_dump(ctx):
    print(dumps(ctx.json['tools'][ctx.tool_name], indent=True))

# ----------------------------------------------------------------------
# ocrd ocrd-tool tool parse-params
# ----------------------------------------------------------------------

@ocrd_tool_tool.command('parse-params')
@parameter_option
@parameter_override_option
@click.option('-j', '--json', help='Output JSON instead of shell variables', is_flag=True, default=False)
@pass_ocrd_tool
def ocrd_tool_tool_parse_params(ctx, parameter, parameter_override, json):
    """
    Parse parameters with fallback to defaults and output as shell-eval'able assignments to params var.
    """
    parameter = set_json_key_value_overrides(parse_json_string_or_file(*parameter), *parameter_override)
    parameterValidator = ParameterValidator(ctx.json['tools'][ctx.tool_name])
    report = parameterValidator.validate(parameter)
    if not report.is_valid:
        print(report.to_xml())
        sys.exit(1)
    if json:
        print(dumps(parameter))
    else:
        for k in parameter:
            print('params["%s"]="%s"' % (k, parameter[k]))
