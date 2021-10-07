import sys, argparse

"""
tinyepubbuilder front end tool
"""

usage = """Usage: tinyepubbuild [-z] <output-name> [-c <cover-image>] [-t <title>]
Description:
    This is a tool to buid epub from a formatted file-list reading from stdin.

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
        A marker which indicates that document linked from a table of contents.
        If there is no index title ("-"), the basename of the file is used as the index title.
"""

def main():
    print(sys.argv[1:])
    print(usage)
    
if __name__ == '__main__':
    main()
