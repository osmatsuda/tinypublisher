import sys, argparse, pathlib

import tinyepubbuilder.reader as reader
import tinyepubbuilder.builder as builder


_FILE_LIST_DESCRIPTION_ = """\
File-list format:
    <file-list>  ::= <entry>+
    <entry> ::= <path> [ "\\t" <use-nav> [ "\\t" <caption> ] ] "\\n"
    <use-nav> ::= <index-title> | "-" | ""
    <caption>  ::= <content-caption> | "-"

    <path>
        A path to XHTML, SVG, or image file. The path should be relative to this
        file list.
        That XHTML and SVG files are used as content documents (EPUB 3.2). Other
        media files are embedded in a XHTML file for each. If you want to embed
        that SVG into XHTML, you should add a <content-caption>.
    <index-title>
        Indicates that document linked from a table of contents.
        If it is specified to "-", the title of content document, text contents,
        or the basename of the file is used as the index title.
    <content-caption>
        When the <path>'s media type is image type, this value used as a content
        of figcaption tag of the wrapping XHTML.
        if the <path> points to a SVG and this cell is specified, the SVG is
        embedded in a XHTML file. Then, if it is "-", this value is the SVG's
        title data or the basename of the file.
"""

def _argparser():
    parser = argparse.ArgumentParser(
        prog='tinyepubbuild',
        description='A tool to buid a EPUB package easily.',
        formatter_class=argparse.RawDescriptionHelpFormatter, 
        epilog=_FILE_LIST_DESCRIPTION_)
    
    parser.add_argument('--unzipped', action='store_true', help='make the package unzipped')
    parser.add_argument('packagename', metavar='package-name', help='EPUB Package directory and make the file <package-name>.epub')
    parser.add_argument('-c', '--cover', metavar='cover-image',
                        help='used for <item properties="cover-image" href="<cover-image>"/>')
    parser.add_argument('-t', '--title', metavar='title',
                        help='if not, <package-name> is used for the book title')
    parser.add_argument('-l', '--language', metavar='language-tag',
                        help='if not, use the `lang` attribute of the content documents. if there is no `lang` attribute, use the `os.environ["LANG"]`')
    parser.add_argument('-a', '--author', metavar='author-name',
                        help='used for <dc:creator> element of the package document')
    parser.add_argument('--id', metavar='identifier',
                        help='used for <dc:identifier> element of the package document')
    parser.add_argument('--uuid', metavar='dns-name', help='if the <identifier> is not specified, use this value for generate the package unique identifier with `uuid5(NAMESPACE_DNS, <dns-name>)`. if both are not specified, generated by `uuid4()`')
    parser.add_argument('-s', '--spine', metavar='file-list', type=pathlib.Path,
                        help='a tab-separated-values file that each line is the spine element for the package. you can also read this list from the standard input')
    return parser

def main():
    argparser = _argparser()
    args = argparser.parse_args()
    try:
        file_list_parser = reader.FileListParser()
        if args.spine:
            if not args.spine.is_file():
                raise Exception(f'"{str(args.spine)}" should be a regular file.')
            file_list_parser.curdir = args.spine.parent
            with open(args.spine) as f:
                package_spec = file_list_parser.parse(f)
        else:
            package_spec = file_list_parser.parse(sys.stdin)
        
        package_spec.cover_image = args.cover
        package_spec.book_title = args.title if args.title is not None else args.packagename
        if args.author:
            package_spec.author = args.author
        package_spec.language_tag = args.language
        package_spec.id = args.id if args.id is not None else None
        package_spec.uuid = args.uuid

        packager = builder.PackageBuilder(args.packagename)
        packager.build_with(package_spec)

        if not args.unzipped:
            packager.zipup()
    except Exception as e:
        print(e)
        argparser.print_help()
    
if __name__ == '__main__':
    main()
