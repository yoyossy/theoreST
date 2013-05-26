#!/usr/bin/env python3
import sys

import options

import bible
import verse_parser

from docutils.parsers import rst
from docutils import statemachine

class BiblePassage(rst.Directive):
    required_arguments = 1
    optional_aguments = 0
    final_argument_whitespace = True

    def run(self):
        '''
        '''
        ref = self.arguments[0]
        #print('****here',ref,options.bible,file=sys.stderr)
        vp = verse_parser.Parser(ref)
        try:
            vrefs = vp.parse_verse_references()
        except verse_parser.ParseException as pe:
            raise self.error("BiblePassage: parse verse ref error: "+str(pe))
        if len(vrefs) != 1:
            raise self.error("BiblePassage: One, and only one, verse reference allowed")
        vref = vrefs[0]
        
        #verses = bible.
        #print(ref,'|',vref.book,'|',type(vref.book))
        
        verse = vref.verse.value if vref.verse else None
        to_verse = vref.to_verse.value if vref.to_verse else None

        rst = bible.get_passage_as_rst('ESV', vref.book.value,
                                       vref.chapter.value, verse, to_verse,
                                       force=False)
        print(rst)
        source = 'Bible Passage'
        include_lines = statemachine.string2lines(rst, 0, convert_whitespace=True)
        self.state_machine.insert_input(include_lines, source)
        return []

rst.directives.register_directive('biblepassage', BiblePassage)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: '+sys.argv[0]+' reference', file=sys.stderr)
        sys.exit(1)
    ref = sys.argv[1]
    vp = verse_parser.Parser(ref)
    try:
        vrefs = vp.parse_verse_references()
    except verse_parser.ParseException as pe:
        raise self.error("BiblePassage: parse verse ref error: "+str(pe))
    if len(vrefs) != 1:
        raise self.error("BiblePassage: One, and only one, verse reference allowed")
    vref = vrefs[0]
    verse = vref.verse.value if vref.verse else None
    to_verse = vref.to_verse.value if vref.to_verse else None

    rst = bible.get_passage_as_rst('ESV', vref.book.value,
                                   vref.chapter.value, verse, to_verse,
                                   force=True)
    print(rst)