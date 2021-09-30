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
    <file-entry> ::= <file-name> [ "\t" [ ">" [ <index-title> ] ] [ "\t" <image-caption> ] ] "\n"

    <file-name>
        A path to xhtml, svg, or media file which can be used in epub3.2.
    ">" [ <index-title> ]
        A marker that indicates a 
"""
