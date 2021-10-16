import sys, argparse

"""
tinyepubbuilder front end tool

Usage: tinyepubbuild [-z] <package-name> [-c <cover-image>] [-t <title>]
Description:
    This is a tool to buid epub from a formatted file-list readable on the standard input.

Options:
    -z, --zipped
    -c, --cover <cover-image>
    -t, --title <title>

File-list format:
    <file-list>  ::= <file-entry>+
    <file-entry> ::= <file-name> [ "\\t" <use-navigation> [ "\\t" <media-caption> ] ] "\\n"
    <use-navigation> ::= ">" [ <index-title> ] | "-"
    <media-caption>  ::= [ <caption> ] | "-"

    <file-name>
        A path to XHTML, SVG, or media file.
        That XHTML and SVG files are used as content documents (EPUB 3.2).
        Other each media file is embedded in a XHTML file. If you want to embed
        that SVG into XHTML, you should add a caption.
    ">" [ <index-title> ]
        A ">" marker which indicates that document linked from a table of contents.
        If there is no index title ("-"), the content dosument's title or 
        the basename of the file is used as the index title.
"""

def parse_args():
    parser = argparse.ArgumentParser(
        prog='tinyepubbuild',
        description='This is a tool to buid epub from a formatted file-list readable on the standard input.')
    
    parser.add_argument('-z', '--zipped', action='store_true',
                        help='make a zipped package: <package-name>.epub')
    parser.add_argument('package-name', help='EPUB Package directory')
    parser.add_argument('-c', '--cover', nargs=1, metavar='cover-image')
    parser.add_argument('-t', '--title', nargs=1, metavar='title')
    return parser.parse_args()

def main():
    args = parse_args()
    print(args)
    print(sys.stdin.read())
    
if __name__ == '__main__':
    main()
