import sys, argparse

import tinyepubbuilder.reader
import tinyepubbuilder.builder

"""
tinyepubbuilder front end tool

Usage: tinyepubbuild [-z] <package-name> \\
       [-c <cover-image>] [-t <title>] [--uuid <dns-name>]
Description:
    This is a tool to buid epub from a formatted file-list readable on the
    standard input.

Options:
    -z, --zipped
    -c, --cover <cover-image>
    -t, --title <title>
    --uuid <dns-name>
"""
_FILE_LIST_DESCRIPTION_ = """\
File-list format:
    <file-list>  ::= <entry>+
    <entry> ::= <path> [ "\\t" <use-nav> [ "\\t" <caption> ] ] "\\n"
    <use-nav> ::= <index-title> | "-" | ""
    <caption>  ::= <content-caption> | "-"

    <path>
        A path to XHTML, SVG, or image file. That XHTML and SVG files are used
        as content documents (EPUB 3.2). Other each media file is embedded in a
        XHTML file. If you want to embed that SVG into XHTML, you should add a
        <content-caption>.
    <index-title>
        If it is specified which indicates that document linked from a table of
        contents.
        If it is specified to "-", the content document's title or the basename
        of the file is used as the index title.
    <content-caption>
        If it is specified to "-" and the <path> points to a SVG file, a SVG's
        title or description content is used.
"""

def arg_parser():
    parser = argparse.ArgumentParser(
        prog='tinyepubbuild',
        description='This is a tool to buid epub from a formatted file-list readable on the standard input.'
        epilog=_FILE_LIST_DESCRIPTION_)
    
    parser.add_argument('-z', '--zipped', action='store_true',
                        help='make a zipped package: <package-name>.epub')
    parser.add_argument('package-name', help='EPUB Package directory')
    parser.add_argument('-c', '--cover', nargs=1, metavar='cover-image',
                        help='path to the cover-image')
    parser.add_argument('-t', '--title', nargs=1, metavar='title',
                        help='if it is not, <package-name> is used for a title')
    parser.add_argument('--uuid', nargs=1, metavar='dns-name',
                        help='generate the package unique identifier with `uuid5(NAMESPACE_DNS, <dns-name>)`. if not be specified, generated by `uuid4()`')
    parser.
    return parser

def main():
    arg_parser = arg_parser()
    args = arg_parser.parse_args()
    try:
        file_list_parser = reader.FileListParser()
        package_spec = file_list_parser.parse(sys.stdin)
        package_spec.add_spec('cover-image', args)
        package_spec.add_spec('title', args)
        package_spec.add_spec('dns-name', args)

        builder = builder.PackageBuilder(args['package-name'])
        builder.make_package_dir()
        builder.build_with(pakage_spec)

        if args.zipped:
            builder.zipup()
    except:
        arg_parser.print_help()
    
if __name__ == '__main__':
    main()
