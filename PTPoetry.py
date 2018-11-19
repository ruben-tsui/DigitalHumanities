# -*- coding: utf-8 -*-
from Book import Book 
from collections import defaultdict
from bs4 import BeautifulSoup
import bs4
from urllib import request
import urllib
import time
import random
import re
import os
import glob
import logging
from tqdm import trange, tqdm_notebook


class PTPoetry(Book):
    """SongShu Dataset
    
    Attributes:
        flat_meta : a list of bookmarks in SonShu extracted from Han-Ji
        flat_passages : a list of ``passages`` in SongShu. 
            Each ``passages`` contain a list of passage in a piece of work.
            i.e., flat_passages = [passages1(list, passages2(list), ...]
                  passages1 = [passage1(str), passage2(str), ...]    
                  
    Args: same as Book class
    
    Methods:
        extract_meta(): Extract meta data from self.paths. Index 3 in path for scroll, 4 for category, 5 for author name, after 5 for the title. The method would check the author name using ###author_bag### automatically.    
        extract_passages(): Extract passages based on indent==2 & padding==0. 
                            If there's no passage in this page, merge all texts into one string.
    """
    
    def __init__(self, date, creator, bookname='PreTangPoetry'):
        Book.__init__(self, bookname, date, creator)
        self.title_candidates = []


    def extract_all(self):
        self.update_rare_chars()
        self.strip_all_irrelevant_tags()

        # preprocessing the PreTangPoetry data to get metadata and bookmarks
        # and separate the passages in every pages
        self.extract_paths()
        self.extract_meta()
        self.extract_passages()
        self.__repr__()

    def extract_meta(self):
        self.flat_meta = []
        for path in self.paths:
            meta = {}
            bookmark_split = path.split('／')

            # Navie implementation
            category = bookmark_split[3].split('\u3000')[0] # 本紀、志、列傳
            scroll   = bookmark_split[4].split('\u3000')[0] # 卷 N 
            categrory_number   = bookmark_split[4].split('\u3000')[1] # 本紀第 N 
            title = '/'.join(bookmark_split[5:]).replace('..[底本：宋元明三朝遞修本]', '')
            meta['category'] = category
            meta['category_number'] = categrory_number
            meta['scroll'] = scroll
            meta['title']  = title
            self.flat_meta.append(meta)

    def extract_passages(self):
        '''Extract passages from SongShu, which divided by the ( indent == 2 & padding == 0 )'''
        self.flat_passages = []

        for body,path in zip(self.flat_bodies, self.paths):
            texts  = body.find_all('div', attrs={'style': True})
            try:
                self.flat_passages.append(
                    self._passage2paragraphs(texts)
                )
            except IndexError as e:
                logging.warning("Not the right indent.{}".format(path))
                self.flat_passages.append(
                    ''.join([text.text for text in texts])
                )


    def _passage2paragraphs(self, texts):
        '''Organize a passage with its paragraph, which is defined using ( indent == 2& padding == 0 )
        '''
        # concatenent the paragraphs with indents not equal to 2 to the previous paragraph
        new_texts = []
        
        # get the pairs of indents and paddings 
        indent_padding_list = self._indent_and_padding(texts)
        
        for text, (indent, padding) in zip(texts, indent_padding_list):
            if indent == 2 and padding == 0:
                # only save the text, without tags
                new_texts.append(
                    ''.join([s for s in text if isinstance(s, bs4.NavigableString)])
                )
            else:
                new_texts[-1] += ''.join([s for s in text if isinstance(s, bs4.NavigableString)])
            
        return new_texts   
        
    def load_htmls(self, path='data/', limit=None):
        ''' loading all files with filename = "bookname_*.html" in path data/;
            limit: if set, this the max. no. of files loaded
        '''
        self.flat_bodies = []
        docList = []
        fileSpec = os.path.join(path, '{}_*.html'.format(self.bookname))
        for fn in glob.glob(fileSpec):
            docList.append(fn)

        maxFiles = len(docList) if limit == None else min(len(docList), limit) 

        for i in trange(maxFiles):
            fn = docList[i] 
            with open(fn, 'r', encoding='utf-8') as file:
                file_read = file.read()
                try:
                    self.flat_bodies.append(BeautifulSoup(file_read, 'lxml'))
                except bs4.FeatureNotFound as e:
                    logging.warning("lxml parser not found, try to use html5lib")
                    self.flat_bodies.append(BeautifulSoup(file_read, "html5lib"))


    def strip_all_irrelevant_tags(self, connect_the_broken_lines=True, html_cutoff=True):
        '''
        remove 標註, page number, and page dividers from the tree structure
        '''
        if html_cutoff:
            flat_bodies = []
            for i in trange(len(self.flat_bodies)):
                item = self.flat_bodies[i]
                try:
                    flat_bodies.append(BeautifulSoup(self._pretty_html(item), "lxml"))
                except bs4.FeatureNotFound as e:
                    logging.warning("lxml parser not found, try to use html5lib")
                    self.flat_bodies.append(BeautifulSoup(self._pretty_html(item), "html5lib"))

            self.flat_bodies = flat_bodies

        self.strip_tag("table", attrs={"class":"page"})
        self.strip_tag("a",     attrs={"href":"#"})
        self.strip_tag("span",  attrs={"style":"display:none;width:;height:;color:red;font-size:13px"})
        self.strip_tag("center")
        logging.info("Remove 標註, page number, and page dividers from the tree structure.")

        if connect_the_broken_lines:
            self.connect_the_broken_lines()
            logging.info("Remove the new lines added by the page dividers, connect the paragraphs before and after the new lines.")


    def extract_paths(self):
        '''extract paths from bookmark in self.flat_bodies list and append paths to self.paths'''
        self.paths = []
        
        regex = re.compile(r"^\S+?／(\w+?)\([Pp]\.\d+\)$")
        for i in trange(len(self.flat_bodies)):
            soup = self.flat_bodies[i]
            # extract "gobookmark" class - it's always the 1st <a> child node of <body>
            bookmark_text = soup.html.body.a.text.strip()
            self.paths.append(bookmark_text)
            title = regex.sub(r"\1", bookmark_text)
            self.title_candidates.append(title)

    def connect_the_broken_lines(self):
        '''
        Remove the new lines added by the page dividers, connect the paragraphs before and after the new lines.
        This method must be run after the self.strip_all_irrelevant_tags.

        TODO: fix the broken new lines in the quoted paragraphs
        '''
        # loop over body in flat_bodies:
        for i in trange(len(self.flat_bodies)):
            item = self.flat_bodies[i]
            # the item here is a bs4 object, so we need to convert it to a string
            string_item = str(item)
            
            # and then, substitute the regex pattern in the html source code in the item
            updated_string_item = re.sub(
                r'<\/div>([^\w]|\n)*?<div style="text-indent:0em;padding-left:0em;">', 
                r"", 
                string_item
            )
            
            # and then, we need to update the variable, item (with regex substituted), back into the flat_bodies list.
            # Note that the updated_string_item has to be converted to bs4 object
            self.flat_bodies[i] = BeautifulSoup(updated_string_item, "lxml")

    def clean_children(self):
        ''' This method replaces self.flat_bodies[] with 
            flat_bodies[].html.body.span
        '''
        N = len(self.flat_bodies)
        for i in trange(N):
            for c in self.flat_bodies[i].body.span.children:
                if isinstance(c, bs4.NavigableString):
                    c.extract()
            self.flat_bodies[i] = self.flat_bodies[i].html.body.span

            
            
            
            

            