#!/usr/bin/env python3
from tokenize import tokenize
import token
from io import BytesIO

single_books = {'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
'Joshua', 'Judges', 'Ruth', 
#'1 Samuel', '2 Samuel', '1 Kings', '2 Kings',
#    '1 Chronicles', '2 Chronicles',
'Ezra', 'Nehemiah', 'Esther',
'Job',
'Psalms', 'Psalm',
'Proverbs', 'Ecclesiastes',
'Song of Songs', 'Song of Solomon',
'Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel',
'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum',
'Habbakuk', 'Zephaniah', 'Haggai', 'Zechariah', 'Malachi',

'Matthew', 'Mark', 'Luke', 'John',
'Acts', 'Romans', 
#'1 Corinthians', '2 Corinthians', 
'Galatians', 'Ephesians', 'Philippians','Colossians',
#'1 Thessalonians', '2 Thessalonians', '1 Timothy', '2 Timothy', 
'Titus', 'Philemon', 'Hebrews', 'James',
#'1 Peter', '2 Peter', '1 John', '2 John', '3 John',
'Jude', 'Revelation'}
double_books = {'Samuel', 'Kings', 'Chronicles', 'Corinthians',
'Thessalonians', 'Timothy', 'Peter'}
triple_books = {'John'}
all_book_names = single_books | double_books | triple_books

class Token:

    value = None    
    
    def __eq__(self, o):
        return type(self) == type(o) and self.value == o.value
        
    def __str__(self):
        return self.value
        
    
class Book(Token):
    def __init__(self, name):
        self.value = name
        
class Number(Token):
    def __init__(self, name):
        self.value = name
        
    def __str__(self):
        return str(self.value)

class SubVerse(Token):
    def __init__(self, name):
        self.value = name

class Colon(Token):
    value = ':'
    
class Comma(Token):
    value = ','
    
class Dash(Token):
    value = '-'
    
class Eof(Token):
    value = '<EOF>'
    
class Unknown(Token):
    def __init__(self, name):
        self.value = name

class Tokeniser:
    '''
    Tokenise the input.
    Use python's own tokeniser in it's stdlib, then transform to our own tokens
    '''
    def __init__(self):
        pass
        
    def tokenise(self, chars):
        tokens = [self._to_bib_token(x) for x in self._py_token_list(chars)]
        tokens = self._transform_for_SoS(tokens)
        tokens = self._transform_for_numbered_books(tokens)
        return tokens

    def _py_token_list(self, s):
        return [(x[0],x[1]) for x in tokenize(BytesIO(s.encode('ascii')).readline) if x[0] != 56]

    def _to_bib_token(self, tok):
        '''translate from python's tokens to our own'''
        tok_id, tok_val = tok
        if tok_id == token.NAME:
            if tok_val in all_book_names:
                return Book(tok_val)
            if tok_val in 'abc':
                return SubVerse(tok_val)
        if tok_id == token.NUMBER:
            return Number(int(tok_val))
        if tok_id == token.OP:
            if tok_val == ':':
                return Colon()
            if tok_val == ',' or tok_val == ';':
                return Comma()
            if tok_val == '-':
                return Dash()
        if tok_id == token.ENDMARKER:
            return Eof()
        return Unknown(tok_val)
        
    def _transform_for_numbered_books(self, toklist):
        '''
        transform token pairs in the list that form numbered books (1 John) into single book tokens
        '''
        rval = []
        maxi = len(toklist) - 2
        i = 0
        while i <= maxi:
            first = toklist[i]
            second = toklist[i + 1]
            if isinstance(first, Number) and isinstance(second,Book):
                if first.value in (1,2) and second.value in double_books\
                  or first.value in (1,2,3) and second.value in triple_books:
                    rval.append(Book(str(first.value)+' '+second.value))
                    i += 2
                    continue
            rval.append(first)
            i += 1
        rval.append(Eof())
        return rval
        
    def _transform_for_SoS(self, toklist):
        rval = []
        maxi = len(toklist) - 3
        i = 0
        while i <= maxi:
            tokens = toklist[i:i+3]
            if all(isinstance(x, Unknown) for x in tokens):
                three_string = ' '.join([x.value for x in tokens])
                #print("########", three_string)
                if three_string.lower() in ['song of solomon', 'song of songs']:
                    rval.append(Book(three_string))
                    i += 3
                    #print('####',three_string)
                    continue
            rval.append(toklist[i])
            i += 1
        return rval+toklist[-2:]
                
        
            

class ParseException(Exception):
    
    def __init__(self, expected, actual, parsed_so_far=[]):
        if isinstance(expected, set):
            self.expected_str = str([x.__name__ for x in expected])
            self.expected_set = expected
        elif isinstance(expected, str):
            self.expected_str = expected
            self.expected_set = None
        self.actual = actual
    
    def __str__(self):
        return "Expected "+self.expected_str+" (actual "+str(self.actual)+")"

class Parser:
    
    def __init__(self, txt):
        self.explicit_txt = None # the explicit text, if any (the 'verse 16' in `verse 16|John 3:16`)
        self.txt = txt            # the text of the reference
        self.index = 0            # current token
        self.refs = []            # verse reference objects
        self.book = None         # current book
        self.chapter = None      # current chapter
        self.text = ""            # text of current verse reference
        self.swallowed = []       # tokens 'swallowed'
        
    def eof(self):
        return self.index >= len(self.tokens) or self.tokens[self.index] == Eof()
        
    def parse_verse_references(self):
        #print([x.value for x in self.tokens])
        if '|' in self.txt:
            parts = self.txt.split('|')
            if len(parts) != 2:
                raise ParseException('One | character',str(len(parts)-1)+" | chars")
            self.explicit_txt, self.txt = parts
            
        self.tokens = Tokeniser().tokenise(self.txt)

        state = self.p_book
        
        while state:
            state = state()
        
        if not self.cur_tok_is(Eof):
            raise ParseException({Eof},self.cur_tok())
        
        if self.explicit_txt:
            if len(self.refs) > 1:
                raise ParseException('One reference with | char',str(len(self.refs))+' references')
            self.refs[0].text = self.explicit_txt
        return self.refs
        
    def p_book(self):
        self.book = self.swallow(Book)
        self.text += self.book.value
        return self.p_chapter
        
    def p_chapter(self):
        self.chapter = self.swallow(Number)
        self.text += ' '+str(self.chapter)
        if self.eof():
            self.refs.append(VerseReference(self.text, self.book, self.chapter, 1))
            self.text = ''
            return None
        if self.cur_tok_is(Comma):
            self.refs.append(VerseReference(self.text, self.book, self.chapter, 1))
            self.text = ''
            self.swallow()
            if self.cur_tok_is(Number):
                return self.p_chapter
            elif self.cur_tok_is(Book):
                return self.p_book
            raise ParseException({Number,Book},self.cur_tok())
        if self.cur_tok_is(Colon):
            self.swallow()
            self.text += ':'
            return self.p_verse
        raise ParseException({Comma,Colon,Eof},self.cur_tok())
        
    def p_verse(self):
        self.verse = self.swallow(Number)
        self.text += str(self.verse)
        self.to_verse = None
        
        if self.cur_tok_is(SubVerse):
            subv = self.swallow(SubVerse)
            self.text += str(subv)
        
        # range (5-17 or 6,7 where two adjacent numbers are separated by comma)
        if self.cur_tok_is(Dash) or \
           self.cur_tok_is(Comma) and self.peek([Number]) and self.peek_ahead(1).value == self.verse.value + 1 and type(self.peek_ahead(2)) != Colon:
            self.swallow()
            self.to_verse = self.swallow(Number)
            self.text += '-'+str(self.to_verse)

        self.refs.append(VerseReference(self.text, self.book, self.chapter, self.verse, self.to_verse))
        self.text = ''
            
        if self.cur_tok_is(Eof):
            return None
            
        if self.cur_tok_is(Comma):  # another verse or a chapter or a book
            self.swallow(Comma)
            
            if self.cur_tok_is(Number) and self.peek([Colon]): # a chapter
                return self.p_chapter
            if self.cur_tok_is(Book): # a book
                return self.p_book
            if self.cur_tok_is(Number): # another verse
                return self.p_verse
            raise ParseException({Number,Book},self.cur_tok())
        raise ParseException({Dash,Comma,Eof,SubVerse},self.cur_tok())
            
        
    def oob(self, index):
        return index >= len(self.tokens) 
        
    def peek(self,ls):
        for i,tok in enumerate(ls):
            peeki = self.index + i + 1
            if self.oob(peeki):
                return tok == Eof
            if type(self.tokens[peeki]) != tok:
                return False
        return True
        
    def cur_tok_is(self, tok):
        #print('cti',self.cur_tok(),tok)
        return type(self.cur_tok()) == tok
            
    def peek_ahead(self,number):
        if self.oob(self.index + number):
            return Eof()
        return self.tokens[self.index + number]
        
    def cur_tok(self):
        if self.oob(self.index):
            return Eof()
        return self.tokens[self.index]
        
    def swallow(self, tok = None):
        curtok = self.cur_tok()
        if tok == None or tok == type(curtok):
            self.swallowed.append(curtok)
            #print('swallow',curtok)
            self.index += 1
            return curtok
        raise ParseException({tok}, self.cur_tok())
        
    
class VerseReference:
    
    def __init__(self, text, book, chapter, verse=None, to_verse=None):
        self.text = text.strip()
        self.book = book
        self.chapter = chapter
        self.verse = verse
        self.to_verse = to_verse
        
    def __eq__(self, o):
        return self.__repr__() == o.__repr__()
            
    def __repr__(self):
        s = '"'+self.text+'" '+str(self.book)+' '+str(self.chapter)
        if self.verse:
            s += ':'+str(self.verse)
            if self.to_verse:
                s += '-'+str(self.to_verse)
        return '('+s+')'
        
    
if __name__ == '__main__':
    tests = {'John 3:16' : [VerseReference('John 3:16', 'John', 3, 16)],
    'John 3,4' : [VerseReference('John 3', 'John', 3, 1), VerseReference('4', 'John', 4, 1)],
    'John John' : {Number},
    'John 3 Mark' : {Comma, Colon, Eof},
    'John 3:16-18' : [VerseReference('John 3:16-18', 'John', 3, 16, 18)],
    'John 3:16-18,21' : [VerseReference('John 3:16-18', 'John', 3, 16, 18), VerseReference('21', 'John', 3, 21)],
    'John 3' : [VerseReference('John 3', 'John', 3, 1)],
    'John 3:16,18' : [VerseReference('John 3:16', 'John', 3, 16), VerseReference('18', 'John', 3, 18)],
    'John 3:16,17' : [VerseReference('John 3:16-17', 'John', 3, 16,17)],
    'John 3, John 4' : [VerseReference('John 3', 'John', 3, 1), VerseReference('John 4', 'John', 4, 1)],
    'John 3:1, John 4' : [VerseReference('John 3:1', 'John', 3, 1), VerseReference('John 4', 'John', 4, 1)],
    'John 3, John 4:1' : [VerseReference('John 3', 'John', 3, 1), VerseReference('John 4:1', 'John', 4, 1)],
    'John 3:1-2,4-5,19,21-26' : [VerseReference('John 3:1-2', 'John', 3, 1, 2), 
                                VerseReference('4-5', 'John', 3, 4, 5),
                                VerseReference('19', 'John', 3, 19),
                                VerseReference('21-26', 'John', 3, 21,26)],
    'John 3:4-5,4:5-6' : [VerseReference('John 3:4-5', 'John', 3, 4, 5), VerseReference('4:5-6', 'John', 4, 5, 6)],
    '1 John 3:4,5,1 John 2:7' : [VerseReference('1 John 3:4-5', '1 John', 3, 4, 5),
                                VerseReference('1 John 2:7', '1 John', 2, 7)],
    'Bill 3:16' : {Book},
    'John 2:2,3 John 1:1' : [VerseReference('John 2:2', 'John', 2, 2),
                            VerseReference('3 John 1:1', '3 John', 1, 1)],
    'verse 16|John 3:16' : [VerseReference('verse 16', 'John', 3, 16)],
    'verse 16|John 3:16,18' : 'Expected One reference with | char (actual 2 references)',
    'John 3:16a' : [VerseReference('John 3:16a', 'John', 3, 16)],
    'John 3:16d' : {Dash,Comma,Eof,SubVerse},
#    'Psalm 103:8-12, Romans 3:23-4, Romans 4:4, 5:20, Ephesians 2:8, 9' :
    'Psalm 103:8-12, Romans 3:23-24, Romans 4:4, 5:20, Ephesians 2:8, 9' :
    [VerseReference('Psalm 103:8-12','Psalm', 103, 8, 12),
     VerseReference('Romans 3:23-24','Romans', 3, 23, 24),
     VerseReference('Romans 4:4', 'Romans', 4, 4),
     VerseReference('5:20', 'Romans', 5, 20),
     VerseReference('Ephesians 2:8-9', 'Ephesians', 2, 8, 9)]
                    
                                # TODO: more tests for errors.
    }

    def ref_list_as_str(verses):
        return ', '.join(x.text for x in verses)

    pass_count = 0
    fail_count = 0
    for txt in sorted(tests):
        print('-------------------',txt)
        p = Parser(txt)
        try:
            vrlist = p.parse_verse_references()
        except ParseException as pe:
            #print(tests[txt],pe.expected,tests[txt] == pe.expected)
            if tests[txt] == pe.expected_set or tests[txt] == str(pe):
                print(txt, ' '*(25-len(txt)),'passed', pe)
                pass_count += 1
            else:
                if isinstance(tests[txt], set):
                    print(txt, '\n\tfailed: expected exception expecting', [x.__name__ for x in tests[txt]])
                else:
                    print(txt, '\n\texpected:', tests[txt])
                print('\t  actual:',pe)
                fail_count += 1
            continue
        if len(vrlist) != len(tests[txt]):
            print(txt,' failed: different length lists:')
            print('\texpected:\t',tests[txt])
            print('\tactual:  \t',vrlist)
            fail_count += 1
            continue
        print('appearance as text:',ref_list_as_str(vrlist))
        for vr,expected in zip(vrlist,tests[txt]):
            if vr == expected:
                print(txt,' '*(25-len(txt)),'passed ',vr)
                pass_count += 1
            else:
                print(txt,'\n\texpected:',expected,'\n\t  actual:',vr)
                fail_count += 1
    print()
    print('passed:',pass_count)
    print('failed:',fail_count)
