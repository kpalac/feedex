#!/usr/bin/python3
# -*- coding: utf-8 -*-

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

#  Author: Karol Pałac (palac.karol@gmail.com)




import numpy as np
import snowballstemmer
import xapian


import pickle
import os
import sys
import re
import chardet
import pyphen




# Constants
DEFAULT_SENTENCE_CHUNKER_RE="""(?:\.\.\.|\.|\?|!|^\s|[\n\t]*?)((?:\s+[A-Z]\w+|\"\s|\'\s|\n+).*?(?:\.\.\.|\.|\?|!| $))(?:\s+[A-Z]\w+|\"\s|\'\s|[\n\t]*?)"""







class DummyStemmer:
    """ This is a dummy to return unstemmed form if smowballstemmer is not provided"""
    def __init__(self, name) -> None: pass
    def stemWord(self, word): return word




class SmallSem:
    """ A simple class that extracts keywords from text based on indexed, stemmed dictionary
            ling - language to use
            models_path - a path where language models are stored 

    """

    def __init__(self, models_path:str, **kwargs) -> None:

        # Init Xapian index pointer to connect if needed
        self.ix_db = None

        # Paths to resources
        self.models_path = models_path
        if not os.path.isdir(self.models_path): self.models_path = os.path.join(os.getcwd(), "models")
        
        # Initialize model headers...
        self.lings = []
        self.ling = {}
        self.load_lings()

        if kwargs.get('ling') is not None: self.set_model(kwargs.get('ling'))

        self.raw_text = ''

        self.tokens = []

        # summarization stuff...
        self.ranked_sents = [] # List of tokenized and ranked sentences

        # Configuration
        self.unknown_term_weight = 5 # Weight for terms not present in vocab. Should be lower for models traines on larger corpuses
        




    def load_lings(self):
        """ Load language headers """
        self.lings = []
        self.ling = {}
        for f in os.listdir(self.models_path):
            
            filename = os.path.join(self.models_path, f)
            if not filename.endswith('_model.pkl'): continue

            try:
                with open(filename, "rb") as ff: self.lings.append(pickle.load(ff))
            except (OSError,) as e:
                sys.stderr.write(f'Error loading {filename} file: {e}')
                continue



    

    def _is_in_ling_names(self, name, name_list):
        """ Compares proposed language name to a provided list """
        if name is None: return False
        for n in name_list:
            if n.lower() == name.lower(): return True
            if n.endswith('*') and name.startswith(n.lower().replace('*','')): return True
        return False


    

    def set_model(self, name, **kwargs):
        """ Set model by language name and point current model to relevant data """
        found = False
        for h in self.lings:
            
            if self._is_in_ling_names(name,h['names']):
                # If model already loaded - do nothing
                if h['names'][0] == self.get_model(): return name
                
                found = True
                self.ling = h
                model_id = h['names'][0]
                
                if h.get('no_index',False):
                    self.index_path = None
                    self.vocab_path = None
                else:
                    self.index_path = os.path.join(self.models_path, f"""{model_id}_index""")
                    self.vocab_path = os.path.join(self.models_path, f"""{model_id}_vocab.pkl""")

                # Init model lists
                self.aliases = h.get('aliases',{})
                self.divs = h.get('divs',())
                self.stops = h.get('stops',())
                self.punctation = h.get('punctation',())
                self.tok_repl = h.get('token_replacements',{})
                self.sent_beg = h.get('sent_beg',())
                self.sent_end = h.get('sent_end',())
                self.commons = h.get('commons_stemmed',())
                self.swadesh = h.get('swadesh',())
 
                self.writing_system = h.get('writing_system',1)
                self.bicameral = h.get('bicameral',1)
 
                self.numerals = h.get('numerals',())
                self.capitals = h.get('capitals',())
                self.name_cap = h.get('name_cap',1)

                # Init stemmer (if not provided, then init dumy stemmer that returns unchanged token
                if h.get('stemmer') is None: self.stemmer = DummyStemmer('dummy')
                else: self.stemmer = snowballstemmer.stemmer(h.get('stemmer','english'))

                # Init syllable splitter
                self.pyphen = pyphen.Pyphen(lang=h.get('pyphen','en_EN'))

                # Clear xapian connection
                if self.ix_db is not None: 
                    self.ix_db.close()
                    self.ix_db = None

                return name

        if not found: 
            sample = kwargs.get('sample',None)
            if sample is None: self.set_model('en')
            else: self.set_model(self.detect_lang(sample))

            return self.get_model()


    def get_model(self): return self.ling.get('names',[None])[0]




    def _xap_connect(self):
        """ Check and connect to xapian """
        if self.ix_db is None and self.index_path is not None: 
            try:
                self.ix_db = xapian.Database(self.index_path)
            except (OSError, xapian.DatabaseError) as e:
                self.ix_db = None
                self.index_path = None
                for i,h in enumerate(self.lings):
                    if self._is_in_ling_names(self.get_model(), h['names']): self.lings[i]['no_index'] = True
                sys.stderr.write(f'Error connecting to {self.index_path} database: {e}')



    def _simple_tokenize(self, text):
        """ Basic tokenization """
        # Make sure a model is loaded
        if self.get_model() is None: self.set_model('unknown', sample=text)
        # Use tokenizing REGEX from model

        raw_tokens = re.findall(self.ling.get('REGEX_tokenizer',"[\w]+"), text)

        rt = []
        for t in raw_tokens:
            # Clear trash that might have been put in token
            t = t.replace(' ','').replace("\n",'').replace("\t",'').replace("\r",'')
            if len(t) < 1: continue
            # This part expands aliases
            if t in self.aliases.keys():
                tts = self.aliases[t]
                for tt in tts: rt.append(tt)
            else: rt.append(t)          

        return rt








    def tokenize(self, text, **kwargs):
        """ Tokenize with normalization and (if specified) stemming and dividing into units 
                stem:bool       should tokens be stemmed?
        """
        
        # Terms are stemmed
        stem = kwargs.get('stem',True)

        # Points to xapian writable db
        writeable_xap = kwargs.get('writeable_xap',None)

        raw_tokens = self._simple_tokenize(text)        

        self.tokens = []
        
        for t in raw_tokens:
            
            if t in self.punctation or t in self.divs: continue
            if self._isnum(t): continue # This is debatable but I decided to ignore numbers as features

            for k,v in self.tok_repl.items(): t = t.replace(k,v)
            
            if stem:
                variant = t.lower()
                stemmed = self.stemmer.stemWord(variant)
                if stemmed in self.stops or variant in self.stops: continue
                tokl = len(stemmed)
                # Unstemmed variants are added as xapian synonyms (might be useful later on ...)
                if writeable_xap is not None and tokl < 150 and len(variant) < 150: # ... but do it only when writable xapian is provided
                    writeable_xap.add_synonym(stemmed, variant)
            else:
                stemmed = t
                tokl = len(stemmed)

            if tokl < 150: self.tokens.append(stemmed)







    def _isnum(self, string):
        """Check if a string is numeral """
        if string.isnumeric(): return True
        tmp = string.replace('.','')
        tmp = tmp.replace(',','')
        if tmp.isnumeric(): return True
        if len(tmp) > 1 and tmp.startswith('-') and tmp[1:].isnumeric(): return True
        if len(tmp) > 0 and self.writing_system in {1,2,} and tmp[0] in self.numerals: return True
        if self.writing_system == 3 and tmp in self.numerals: return True
        return False



    def _case(self, t:str):
        """ Check token's case and code it into (0,1,2)"""
        if self.writing_system == 1:
            if t.islower(): case = 0
            elif t.isupper() and len(t) > 1: case = 2
            elif t[0].isupper(): case = 1
            else: case = 3

        elif self.writing_system == 2:
            if t in self.capitals: case = 1

        return case






    def get_related(self, string, depth=100):
        """ List terms with similar contexts to given terms """

        if self.get_model() is None: self.set_model('en') # Load english model as default

        self._xap_connect()
        if self.ix_db is None: return [] # If xapian is unavailable, then there is no data for contexts...

        string = self.stemmer.stemWord(string.lower())
        contexts_fr = {}
        for doc in self.ix_db.postlist(string):
            doc_id = doc.docid
            for pterm in self.ix_db.termlist(doc_id):
                t = pterm.term.decode("utf-8")
                contexts_fr[t] = contexts_fr.get(t,0) + 1

        contexts = []
        for k,v in contexts_fr.items():
            contexts.append([k,v])
        
        if len(contexts) == 0: return []
        contexts.sort(key=lambda x: x[1], reverse=True)
        contexts = contexts[:int(depth)]

        # Normalize weights
        max_weight = contexts[0][1]
        for i,c in enumerate(contexts):
            contexts[i][1] = contexts[i][1]/max_weight
        
        return contexts








    def extract_features(self, text, depth=10):
        """ Main method for extracting keywords from a given string. 
            Returns a list of tuples with n strongest candidates with weights and stemmed forms"""        

        token = {}
        tokens = []
        token_freqs = {}
        token_tf_idfs = {}

        self.tokenize(text, units=False, stem=False)

        # Lazily connect to xapian
        self._xap_connect()
        if self.ix_db is None: use_xap = False
        else: use_xap = True

        # Populate token list with dict
        for i,t in enumerate(self.tokens):
            
            term = self.stemmer.stemWord(t.lower())
            if t in self.stops or term in self.stops: continue

            token = {'pos':i, 'var':t, 'term':term}
            tokens.append(token.copy())


        # Create variant frequency distribution
        for t in tokens:
            fr = token_freqs.get(t['var'],[0,None])[0] + 1
            token_freqs[t['var']] = (fr, t['term'])

        # Get metrics that might be useful...
        doc_len = len(tokens)

        # Ignore empty documents
        if doc_len == 0: return []

        # Calculate tf-idf-like weight for each variant based on xapian frequencies
        for k,t in token_freqs.items():
            klower = k.lower()
            term = t[1]
            v = t[0]
            #matched_docs = 0
            #for t in self.ix_db.postlist(k): matched_docs += 1
            #if matched_docs == 0: idf = 1
            #else: idf = log10(n_docs/matched_docs)
            #tf = v/doc_len
            #tf_idf = tf * idf

            if use_xap:
                if klower in self.stops: 
                    token_tf_idfs[k] = 0
                    continue
                
                fr = self.ix_db.get_termfreq(term)
                if fr == 0:
                    fr = 1
                    v = v * self.unknown_term_weight # I decided to boost unknown vocab. To be seen if this works ...
                
                # Boost upper cases for bicameral models
                case = self._case(k)
                if case != 0: 
                    if self.writing_system == 1 and self.bicameral == 1:
                        if self.name_cap == 1:
                            if case == 1: v *= 2
                            elif case == 2: v *= 3
                        elif self.name_cap == 2:
                            if case == 1: v *= 1.5
                            elif case == 2: v *= 3
                    elif self.writing_system == 2 and self.bicameral == 1:
                        if self.name_cap == 1:
                            if case == 1: v *= 3
                            elif case == 2: v *= 4
                        elif self.name_cap == 2:
                            if case == 1: v *= 3
                            elif case == 2: v *= 4

                # Build TF-IDFish measure
                prob = fr
                tf = v
                tf_idf = tf / prob

                token_tf_idfs[k] = tf_idf
            
            # If no xapian db then use crude heuristics based on common word lists (uncommon = interesting)
            else: 
                if klower in self.stops: token_tf_idfs[k] = 0
                elif k in self.commons: token_tf_idfs[k] = 0
                elif k in self.swadesh: token_tf_idfs[k] = 0
                else: token_tf_idfs[k] = v
            



        # Generate vocab and assign IDs to unique tokens
        vocab = {}
        i = 0
        for k,v in token_freqs.items():
            i += 1
            vocab[k] = (i, token_tf_idfs[k],)
        
        # Generate inverted vocab fo easy lookup
        inv_vocab = {}
        for k,v in vocab.items(): inv_vocab[v[0]] = (k, v[1])

        # Generate main keyword dictionary to sort later ...
        kwds = {}
        for t in tokens:
            t['id'] = vocab[t['var']][0]
            t['tf_idf'] = token_tf_idfs[t['var']]
            kwds[t['var']] = (t['id'], t['term'], t['tf_idf'])



        #######
        # Next comes extracting important word pairs using coocurrence matrix. Not really necessary to do it with NymPy,
        cooc_mx = np.zeros( (max(inv_vocab.keys())+1, max(inv_vocab.keys())+1) )
        for k,v in vocab.items():
            for i,t in enumerate(tokens):
                if t['id'] == v[0] and i < doc_len-1:
                    other_id = tokens[i+1]['id']
                    cooc_mx[v[0]][other_id] += 1

        ixs1, ixs2 = np.where(cooc_mx > 1) # Use 

        composites = []
        for i in range(len(ixs1)):
            t1 = inv_vocab[ixs1[i]][0]
            t2 = inv_vocab[ixs2[i]][0]
            t1_stem = self.stemmer.stemWord(t1.lower())
            t2_stem = self.stemmer.stemWord(t2.lower())

            composites.append(
            [f"""{t1} {t2}""", cooc_mx[ixs1[i]][ixs2[i]] * (inv_vocab[ixs1[i]][1]+inv_vocab[ixs2[i]][1])/2, # The weight of each pair is average of weights of components
             f"""{t1_stem} {t2_stem}""",
            ]
            )
        
        # Generate single keyword list
        keywords = []
        for k,v in kwds.items():
            keywords.append([k, v[2], v[1],])
        # ... and merge it with keyword pairs
        keywords = keywords + composites

        if len(keywords) == 0: return []

        # Finally sort the whole list and return n top results
        keywords.sort(key=lambda x: x[1], reverse=True)
        keywords = keywords[:int(depth)]

        # Normalize weights
        max_weight = keywords[0][1]
        for i,kw in enumerate(keywords):
            keywords[i][1] = keywords[i][1]/max_weight
        
        return keywords








    def chunk_sents(self, text, **kwargs):
        """ Summarize a text into N sentences """
        features = self.extract_features(text, 100)
        
        self.ranked_sents = []
        sents_raw = re.findall(self.ling.get('sentence_chunker', DEFAULT_SENTENCE_CHUNKER_RE), text)

        # Tokenize and rank each sentence separately and create a list
        for s in sents_raw:

            if type(s) is not str: continue

            s = s.replace("\n",'').replace("\t",'').replace('\r','')
            self.tokenize(s, units=False, stem=True)

            # Construct a string for ranking
            sent_string = ' '
            for t in self.tokens: sent_string = f"""{sent_string}{t} """

            weight = 0
            for f in features:
                matched = sent_string.lower().count(f' {f[2].lower()} ')
                weight += matched * f[1]        

            weight = float(weight)
            self.ranked_sents.append( (s, weight) )
            
        return self.ranked_sents






    def summarize(self, level=50, **kwargs):
        """ Summarize previously chunked document by selecting weight threshold (like a rising water level covering unimportant sentences)"""
        sep = kwargs.get('separator','')
        if not (level >= 0 and level <= 100): raise ValueError('Summary level must be between 0 and 100')

        # Sort weights for normalization
        sents = []

        if level == 0: thres = 0
        else:
            for i,s in enumerate(self.ranked_sents): sents.append( (i,s[1]) )
            sents.sort(key=lambda x: x[1])

            divider = int(round(len(sents)*level/100, 0) - 1)
            thres = sents[divider][1]

        if thres <= sents[0][1]: return None

        summ_doc = ''
        last_cand = 0
        for i,s in enumerate(self.ranked_sents):
            if s[1] >= thres:
                if i - last_cand > 1: summ_doc = f'''{summ_doc}{sep}{s[0]}'''
                else: summ_doc = f'''{summ_doc} {s[0]}'''
                last_cand = i

        return summ_doc







    def detect_lang(self, sample):
        """ Crude language detection from sample """
        tokens = sample.split(' ')
        if len(tokens) >= 300: tokens = tokens[:300]
        chars = sample
        if len(chars) >= 200: chars = chars[:200]


        freq_dist = {}
        for l in self.lings:
            lname = l.get('names',[None])[0]
            freq_dist[lname] = 0
            if l.get('writing_system') == 1:
                for t in tokens:
                    if t in l.get('stops',()): freq_dist[lname] += 1
                    elif t in l.get('swadesh',()): freq_dist[lname] += 1
                    elif t in l.get('commons',()): freq_dist[lname] += 1

            elif l.get('writing_system') == 2:
                for c in sample:
                    if c in l.get('stops',()): freq_dist[lname] += 1
                    elif c in l.get('swadesh',()): freq_dist[lname] += 1
                    elif c in l.get('commons',()): freq_dist[lname] += 1


        max_fr = max(freq_dist.values())
        candidates = [key for key, value in freq_dist.items() if value == max_fr]

        return candidates[0]
















class SmallSemTrainer:
    """ A helper class for training models (basically indexing vocab)"""

    def __init__(self, lang:str, models_path:str, **kwargs) -> None:

        self.ke = SmallSem(models_path, lang=lang)
        self.ke.set_model(lang)

        # Init Xapian index
        self.ix_db = xapian.WritableDatabase(self.ke.index_path, xapian.DB_CREATE_OR_OPEN)
        self.ix_tg = xapian.TermGenerator()

        # Counters
        self.doc_counter = 0
        self.sent_counter = 0

        # Semantic Units for vectorization
        self.units = []





    def learn_text(self, text:str, doc_id, **kwargs):
        """ Indexes given text and adds terms to vocab 
            doc_id = int    Main document counter """
        weight = kwargs.get('weight', 1)
        self.ke.raw_text = text
        sents = re.findall(self.ke.ling.get('sentence_chunker', DEFAULT_SENTENCE_CHUNKER_RE), text)
        
        self.units.clear()
        for s in sents: 
            self.ke.tokenize(s, writeable_xap=self.ix_db)
            self.units.append(self.ke.tokens.copy())


        for i,u in enumerate(self.units):

            doc_string = ''
            for t in u: doc_string = f'{doc_string} {t}'

            #did = f'{doc_id};{i}'
            #doc.add_boolean_term(f'DID {did}')
            #doc.add_boolean_term(f'UID {i}')
            #doc.set_data(did)
            doc = xapian.Document()
            self.ix_tg.set_document(doc)
            self.ix_tg.index_text_without_positions(doc_string, weight)
            self.ix_db.add_document(doc)






    def learn_from_dir(self, directory:str, **kwargs):
        """ Loads all files from a folder and indexes them"""
        weight = kwargs.get('weight', 1)
        for i,f in enumerate(os.listdir(directory)):
            filename = os.path.join(directory, f)
            try:
                # Detect encodng...
                with open(filename, 'rb') as file:
                    contents = file.read()
                    encoding = chardet.detect(contents)['encoding']
                with open(filename, 'r', encoding=encoding) as file:
                    contents = file.read()
            except (OSError, UnicodeDecodeError,) as e:
                print(f'Error loading {filename} file: {e}')
                continue
            
            print(f'Indexing {filename} (encoding: {encoding})...')
            self.learn_text(contents, i, weight=weight)
            print(f'Done.')






        














HELP_STRING="""
Extracts keywords from text file based on pretrained vocabulary
Options:

    --models-path=PATH      Folders with stored language models (if not provided - current directory will be used)
    --lang=LANG             Which anguage to use?      

    --keywords FILE         Extract keyword list from a given text file
    --depth=INT             How many best keywords to extract?

    --summarize FILE        Summarize file
    --level=1..100          Summarization level

    --related TERM          Show n (--depth) best context words for a term
    --freq TERM             Term's freqiency in a model
    
    --learn-from-dir DIR    Learn vocab and train on all text files in a folder
    --weight=INT            Dir's weight/significance in model                
    
    --help, -h              Show this message



"""







if __name__ == '__main__':

    par_len = len(sys.argv)
 
    index_dir = None
    lang = None
    term = None
    action = None
    depth = 10
    level = 50
    weight = 1
    separator = ''
    file = None
    models_path = ''
    matrix_file = ''


    if  par_len > 1:
        for i, arg in enumerate(sys.argv):

            if i == 0: continue

            if arg == '--learn-from-dir' and par_len > i:
                index_dir = sys.argv[i+1]      
                action = 'learn_from_dir'
                break


            elif arg == '--freq' and par_len > i:
                term = sys.argv[i+1]      
                action = 'freq'
                break

            elif arg == '--related' and par_len > i:
                term = sys.argv[i+1]      
                action = 'related'
                break

            elif arg == '--keywords' and par_len > i:
                file = sys.argv[i+1]      
                action = 'keywords'
                break

            elif arg == '--summarize' and par_len > i:
                file = sys.argv[i+1]      
                action = 'summarize'
                break


            elif arg.startswith('--lang=') and arg != '--lang=':
                lang = arg.split('=')[1]

            elif arg.startswith('--models_path=') and arg != '--models_path=':
                models_path = arg.split('=')[1]
            
            elif arg.startswith('--depth=') and arg != '--depth=':
                depth = arg.split('=')[1]

            elif arg.startswith('--weight=') and arg != '--weight=':
                weight = int(arg.split('=')[1])

            elif arg.startswith('--level=') and arg != '--level=':
                level = arg.split('=')[1]

            elif arg.startswith('--separator=') and arg != '--separator=':
                separator = arg.split('=')[1]



            elif arg in {'-h','-help','--help',}:
                print(HELP_STRING)
                sys.exit(0)




    if action in {'learn_from_dir', 'freq', 'related', 'keywords', 'summarize',}:
        
        if action == 'learn_from_dir': 
            kl = SmallSemTrainer(lang, models_path)
            kl.learn_from_dir(index_dir, weight=weight)

        elif action == 'freq':
            lp = SmallSem(models_path, ling=lang)
            term = lp.stemmer.stemWord(term.lower())
            print(f'Stemmed form: {term}')
            print(f'Collection frequency: {lp.ix_db.get_termfreq(term)}')

        elif action == 'related':
            lp = SmallSem(models_path, ling=lang)
            for c in lp.get_related(term, depth): print(c)

        elif action == 'keywords':
            lp = SmallSem(models_path, ling=lang)
            try:
                # Detect encodng...
                with open(file, 'rb') as f:
                    contents = f.read()
                    encoding = chardet.detect(contents)['encoding']
                with open(file, 'r', encoding=encoding) as f:
                    contents = f.read()
            except OSError as e:
                print(f'Error loading {file} file: {e}')
                sys.exit(1)

            kwrds = lp.extract_features(contents, depth=depth)
            for kw in kwrds: print(kw)


        elif action == 'summarize':
            lp = SmallSem(models_path, ling=lang)
            try:
                # Detect encodng...
                with open(file, 'rb') as f:
                    contents = f.read()
                    encoding = chardet.detect(contents)['encoding']
                with open(file, 'r', encoding=encoding) as f:
                    contents = f.read()
            except OSError as e:
                print(f'Error loading {file} file: {e}')
                sys.exit(1)
            
            lp.chunk_sents(contents)
            print( lp.summarize(int(level), separator=separator) )
