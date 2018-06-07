# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Alexandar P. Mechev
# All rights reserved.
#
# This software is licensed as described in the file LICENSE.md, which
# you should have received as part of this distribution.

"""
.. module:: GRID_LRT.Token 
   :platform: Unix
   :synopsis: Set of tools for manually and automatically creating tokens

.. moduleauthor:: Alexandar Mechev <LOFAR@apmechev.com>

>>> #Example creation of a token of token_type 'test'
>>> from GRID_LRT.get_picas_credentials import picas_cred
>>> pc=picas_cred() #Gets picas_credentials
>>> 
>>> th=Token.Token_Handler( t_type="test", srv="https://picas-lofar.grid.surfsara.nl:6984", uname=pc.user, pwd=pc.password, dbn=pc.database) #creates object to 'handle' Tokens
>>> th.add_overview_view()
>>> th.add_status_views() #Adds 'todo', 'done', 'locked' and 'error' views
>>> th.load_views() 
>>> th.views.keys()
>>> th.reset_tokens(view_name='error') # resets all tokens in 'error' view
>>> th.set_view_to_status(view_name='done','processed')
"""

import sys
import os
import shutil
import ConfigParser
import pdb
import itertools
import yaml
import time
import tarfile
if 'couchdb' not in sys.modules:
    from GRID_LRT import couchdb
from couchdb.design import ViewDefinition


__author__ = "Alexandar P. Mechev"
__copyright__ = "2016 Alexandar P. Mechev"
__credits__ = ["Alexandar P. Mechev", "Natalie Danezi", "J.B.R. Oonk"]
__license__ = "GPL 3.0"
__version__ = "0.2.4"
__maintainer__ = "Alexandar P. Mechev"
__email__ = "LOFAR@apmechev.com"
__status__ = "Production"


def reset_all_tokens(token_type,picas_creds):
    th=Token_Handler(t_type=token_type, 
            uname=picas_creds.user, pwd=picas_creds.password, dbn=picas_creds.database)
    th.load_views()
    for view in th.views.keys():
        if view !='overview_total':
            th.reset_tokens(view)

def purge_tokens(token_type,picas_creds):
    th=Token_Handler(t_type=token_type,
            uname=picas_creds.user, pwd=picas_creds.password, dbn=picas_creds.database)
    th.load_views()
    th.purge_tokens()

class Token_Handler:
    """

    The Token_Handler class uses couchdb to create, modify and delete
    tokens and views, to attach files, or download attachments and to 
    easily modify fields in tokens. It's initiated with the token_type, 
    server, username, password and name of database. 

    """

    def __init__(self, t_type="token", srv="https://picas-lofar.grid.surfsara.nl:6984", uname="", pwd="", dbn=""):
        """
        >>> #Example creation of a token of token_type 'test'
        >>> from GRID_LRT.get_picas_credentials import picas_cred
        >>> pc=picas_cred() #Gets picas_credentials
        >>> 
        >>> th=Token.Token_Handler( t_type="test", srv="https://picas-lofar.grid.surfsara.nl:6984", uname=pc.user, pwd=pc.password, dbn=pc.database ) #creates object to 'handle' Tokens
        >>> th.add_overview_view()
        >>> th.add_status_views() #Adds 'todo', 'done', 'locked' and 'error' views
        >>> th.load_views() 
        >>> th.views.keys()
        >>> th.reset_tokens(view_name='error') # resets all tokens in 'error' view
        >>> th.set_view_to_status(view_name='done','processed')
        """
        if t_type:
            self.t_type = t_type
        else: 
            raise Exception("t_type not defined!")
        self.Picas_User = uname
        self.Picas_DB = dbn
        self.Picas_Passwd = pwd
        self.server = srv
        self.db = self.get_db(self.Picas_User, self.Picas_Passwd, self.Picas_DB, self.server)
        self.views = {}
        self.tokens = {}

    def get_db(self, uname, pwd, dbn, srv):
        """Logs into the Couchdb server and returns the database requested. Returns a couchDB database object

        :param uname: The username to log into CouchDB with
        :type uname: str
        :param pwd: The CouchDB password 
        :type pwd: str
        :param dbn: The CouchDB Database Name 
        :type dbn: str
        :param srv: URL of the CouchDB Server
        :type srv: str
        :return: A CouchDB Database Object
        :rtype: :class:`~couchdb.client.Database` 
        """
        server = couchdb.Server(srv)
        server.resource.credentials = (uname, pwd)
        db = server[dbn]
        return db

    def create_token(self, keys={}, append="", attach=[]):
        '''Creates a token, appends string to token ID if requested and adds user requested keys through the dict keys{} 

        :param keys: A dictionary of keys, which will be uploaded to the CouchDB document.
            The supported values for a key are str,int,float and dict
        :type keys: dict
        :param append: A string which is appended to the end of the tokenID, useful for
            adding an OBSID for example
        :type append: str
        :param attach: A 2-item list of file to be attached to the token. The first value is the file handle and the second is a string with the attachment name. ex: [open('/home/apmechev/file.txt','r'),"file.txt"]
        :type attach: list
        :return: A string with the token ID
        :rtype: str
        '''
        default_keys = {
            '_id': 't_'+self.t_type+"_",
            'type': self.t_type,
            'lock': 0,
            'done': 0,
            'hostname': '',
            'scrub_count': 0,
            'output': "",
            'created': time.time()
            } 
        keys = dict(itertools.chain(keys.iteritems(), default_keys.iteritems()))
        self.append_id(keys, append)
        self.tokens[keys["_id"]] = keys
        self.db.update([keys])
        if attach:
            self.add_attachment(keys['_id'], attach[0], attach[1])
        return keys['_id']  # returns the token ID

    def append_id(self, keys, app=""):
        """ Helper function that appends a string to the token ID"""
        keys["_id"] += app

    def load_views(self):
        """Helper function to get the current views on the database. 
        Updates the internal self.views variable
        """
        db_views = self.db.get("_design/"+self.t_type)
        if db_views == None:
            print("No views found in design document")
            return
        self.views = db_views["views"]

    def delete_tokens(self, view_name="test_view", key=["", ""]):
        """Deletes tokens from view view_name

            exits if the view doesn't exist

            User can select which tokens within the view to delete

            >>> t1.delete_tokens("todo",["OBSID","L123456"]) #Only deletes tokens with OBSID key = L123456
            >>> t1.delete_tokens("error") # Deletes all error tokens

        :param view_name: Name of the view from which to delete tokens
        :type view_name: str
        :param key: key-value pair that selects which tokens to delete (by default empty == delete all token)
        :type key: list
        """
        v = self.list_tokens_from_view(view_name)
        to_delete=[]
        for x in v:
            document = self.db[x['key']]
            if key[0] == "":
                pass
            else:
                if not document[key[0]] == key[1]:
                    continue
            print("Deleting Token "+x['id'])
            to_delete.append(document)
        self.db.purge(to_delete)
        #    self.tokens.pop(x['id'])
        # TODO:Pop tokens from self

    def add_view(self, view_name="test_view", cond='doc.lock > 0 && doc.done > 0 && doc.output < 0 ',emit_value='doc._id',emit_value2='doc._id'):
        """Adds a view to the db, needs a view name and a condition. Emits all tokens with the type of Token_Handler.t_type, that also match the condition

        :param view_name: The name of the new view to be created
        :type view_name: str
        :param cond: A string containing the condition which all tokens of the view must match. It can include boolean operators '>', '<'and '&&'. The token's fields are refered to as 'doc.field'
        :type cond: str
        :param emit_value: The (first) emit value that is returne by the view. If you look on couchdb/request the tokens from the view, you'll get two values. This will be the first (typically the token's ID)
        :type emit_value: str
        :param emit_value2: The second emit value. You can thus return the token's ID and its status for example
        :type emit_value2: str
        """
        generalViewCode = '''
        function(doc) {
           if(doc.type == "%s") {
            if(%s) {
              emit(%s, %s );
            }
          }
        }
        '''
        view = ViewDefinition(self.t_type, view_name, generalViewCode % (self.t_type, cond, emit_value, emit_value2))
        self.views[view_name] = view
        view.sync(self.db)

    def add_mapreduce_view(self, view_name="test_mapred_view", cond='doc.PIPELINE_STEP == "pref_cal1" '):
        """
        While the overview_view is applied to all the tokens in the design document, this 'mapreduce' view
        is useful if instead of regular view, you want to filter the tokens and display the user with 
        a 'mini-oververview' view. This way you can check the status of a subset of the tokens.

        """
        overviewMapCode = '''
function(doc) {
   if(doc.type == "%s" )
      if(%s){
        {
       if (doc.lock == 0 && doc.done == 0){
          emit('todo', 1);
       }
       if(doc.lock > 0 && doc.status == 'downloading' ) {
          emit('downloading', 1);
       }
       if(doc.lock > 0 && doc.done > 0 && doc.output == 0 ) {
          emit('done', 1);
       }
       if(doc.lock > 0 && doc.output != 0 && doc.output != "" ) {
          emit('error', 1);
       }
       if(doc.lock > 0 && doc.status == 'launched' ) {
          emit('waiting', 1);
       }
       if(doc.lock > 0  && doc.done==0 && doc.status!='downloading' ) {
          emit('running', 1);
       }
     }
   }
}
'''
        overviewReduceCode = '''
function (key, values, rereduce) {
   return sum(values);
}
'''
        overview_total_view = ViewDefinition(self.t_type, view_name,
                                             overviewMapCode % (self.t_type, cond),
                                             overviewReduceCode)
        self.views['overview_total'] = overview_total_view
        overview_total_view.sync(self.db)



    def add_overview_view(self):
        """ Helper function that creates the Map-reduce view which makes it easy to count
            the number of jobs in the 'locked','todo','downloading','error' and 'running' states
        """
        overviewMapCode = '''
function(doc) {
   if(doc.type == "%s") {
       if (doc.lock == 0 && doc.done == 0){
          emit('todo', 1);
       }
       if(doc.lock > 0 && doc.status == 'downloading' ) {
          emit('downloading', 1);
       }
       if(doc.lock > 0 && doc.done > 0 && doc.output == 0 ) {
          emit('done', 1);
       }
       if(doc.lock > 0 && doc.output != 0 ) {
          emit('error', 1);
       }
       if(doc.lock > 0 && doc.status == 'launched' ) {
          emit('waiting', 1);
       }
       if(doc.lock > 0  && doc.done==0 && doc.status!='downloading' ) {
          emit('running', 1);
       }
   }
}
'''
        overviewReduceCode = '''
function (key, values, rereduce) {
   return sum(values);
}
'''
        overview_total_view = ViewDefinition(self.t_type, 'overview_total',
                                             overviewMapCode % (self.t_type),
                                             overviewReduceCode)
        self.views['overview_total'] = overview_total_view
        overview_total_view.sync(self.db)

    def add_status_views(self):
        """ Adds the 'todo', locked, done and error views. the TODO view is necessary for the 
        worker node to find an un-locked token
        """
        self.add_view(view_name="todo", cond='doc.lock ==  0 && doc.done == 0 ')
        self.add_view(view_name="locked", cond='doc.lock > 0 && doc.done == 0 ')
        self.add_view(view_name="done", cond='doc.status == "done" ')
        self.add_view(view_name="error", cond='doc.output != 0 ', emit_value2='doc.output')
    
    def del_view(self, view_name="test_view"):
        '''Deletes the view with view name from the _design/${token_type} document
            and from the token_Handler's dict of views

        :param view_name: The name of the view which should be removed
        :type view_name: str
        '''
        db_views = self.db.get("_design/"+self.t_type)
        db_views["views"].pop(view_name, None)
        self.views.pop(view_name, None)
        self.db.update([db_views])

    def remove_Error(self):
        ''' Removes all tokens in the error view
        '''
        cond = "doc.lock > 0 && doc.done > 0 && doc.output > 0"
        self.add_view(view_name="error", cond=cond)
        self.delete_token("error")

    def reset_tokens(self, view_name="test_view", key=["", ""], del_attach=False):
        """ resets all tokens in a view, optionally can reset all tokens in a view
            who have key-value pairs matched by key[0],key[1]
            
            >>> t1.reset_token("error")
            >>> t1.reset_token("error",key=["OBSID","L123456"])
            >>> t1.reset_token("error",key=["scrub_count",6])
        """
        v = self.list_tokens_from_view(view_name)
        to_update = []
        for x in v:
            document = self.db[x['key']]

            if key[0] != "" and document[key[0]] != key[1]:  # make it not just equal
                continue
            try:
                document['status'] = 'todo'
            except KeyError:
                pass
            document['lock'] = 0
            document['done'] = 0
            document['scrub_count'] += 1
            document['hostname'] = ''
            document['output'] = ''
            if del_attach:
                    if "_attachments" in document:
                        del document["_attachments"]
            to_update.append(document)
        self.db.update(to_update)
        return (to_update)

    def add_attachment(self, token, filehandle, filename="test"):
        """Uploads an attachment to a token

        Args:
            :param token: The Token _id as recorded in the CouchDB database 
            :type token: str
            :param filehandle: the file handle to the file which to upload open(filepath,'r')
            :type tok_config: os.file()
            :param filename: The name of the attachment 
            :type tok_config: str

        """
        self.db.put_attachment(self.db[token], filehandle, filename)

    def list_attachments(self, token):
        """Lists all of the filenames attached to a couchDB token
        """
        return self.db[token]["_attachments"].keys()

    def get_attachment(self, token, filename, savename=None):
        """Downloads an attachment from a CouchDB token. Optionally
            a save name can be specified. 
        """
        try:
            attach = self.db.get_attachment(token, filename).read()
        except AttributeError:
            print("error getting attachment")
            return ""
        if "/" in filename:
            savefile = filename.replace("/", "_")
        if savename!=None:
            savefile = savename
        with open(savefile, 'w') as f:
            for line in attach:
                f.write(line)
        return os.path.abspath(savefile)

    def list_tokens_from_view(self, view_name):
        self.load_views()
        if view_name in self.views:
            view = self.views[view_name]
        else:
            print("View Named "+view_name+" Doesn't exist")
            return
        v = self.db.view(self.t_type+"/"+view_name)
        return v
  
    def archive_tokens_from_view(self,viewname,delete_on_save=False):
         to_del=[]
         for token in self.list_tokens_from_view(viewname):
             self.archive_a_token(token['id'],delete_on_save)
             to_del.append(self.db[token['id']])
         if delete_on_save:
             self.db.purge(to_del)


    def archive_tokens(self,delete_on_save=False, compress=True):
        """Archives all tokens and attachments into a folder

        """
        os.mkdir(self.t_type)
        os.chdir(self.t_type)
        self.load_views()
        for view in self.views.keys():
            if view=='overview_total':
                continue 
            self.archive_tokens_from_view(view, delete_on_save)
        result_link = os.getcwd()
        os.chdir('..')
        if compress:
            with tarfile.open(name="tokens_"+self.t_type+".tar.gz",mode='w:gz') as t_file:
                t_file.add(self.t_type+"/")
                result_link=t_file.name
                shutil.rmtree(self.t_type+"/")
        return(result_link)


    def archive_a_token(self,token_ID,delete=False):
        "Dumps the token data into a yaml file and saves the attachments"
        data=self.db[token_ID]
        yaml.dump(data,open(token_ID+".dump",'w'))
        for f in self.list_attachments(token_ID):
            fname=f.replace('/','-')
            self.get_attachment(token_ID,f,token_ID+"_attachment_"+str(fname))

    def clear_all_views(self):
        """Iterates over all views in the design document 
        and deletes all tokens from those views. Finally, removes
        the views from the database"""
        self.load_views()
        for view in self.views.keys():
            if view !='overview_total':
                self.delete_tokens(view)
            self.del_view(view)
        self.load_views()
        return self.views

    def purge_tokens(self):
        """ Deletes ALL tokens associated with this token_type
        and removes all views. Also removes the design document from 
        the database"""
        self.clear_all_views()
        del(self.db['_design/'+self.t_type])
        return None

    def set_view_to_status(self, view_name, status):
        """Sets the status to all tokens in 'view' to 'status
            eg. Set all locked tokens to error or all error tokens to todo
        """
        v = self.list_tokens_from_view(view_name)
        to_update = []
        for x in v:
            document = self.db[x['key']]
            document['status'] = str(status)
            document['lock'] = 1
            to_update.append(document)
        self.db.update(to_update)

class TokenSet(object):
    """ The TokenSet object can automatically create a group of tokens from a
    yaml configuration file and a dictionary. It keeps track internally of
    the set of tokens and allows users to batch attach files to the entire TokenSet or alter
    fields of all tokens in the set. 

    """
    def __init__(self,th=None,tok_config=None):
        """ The TokenSet object is created with a TokenHandler Object, which is 
        responsible for the interface to the CouchDB views and Documents. This also ensures
        that only one job type is contained in a TokenSet. 

        Args:
            :param th: The TokenHandler associated with the job tokens        
            :type th: GRID_LRT.Token.TokenHandler
            :param tok_config: Location of the token yaml file on the host FileSystem
            :type tok_config: str
            :raises: AttributeError, KeyError

        """
        self.th=th
        self.__tokens=[]
        if not tok_config:
            self.token_keys={}
        else:
            with open(tok_config,'r') as optfile:
                self.token_keys=yaml.load(optfile)['Token']

    def create_dict_tokens(self,iterable={},id_prefix='SB',id_append="L000000",key_name='STARTSB',file_upload=None):
        """ A function that accepts a dictionary and creates a set of tokens equal to 
            the number of entries (keys) of the dictionary. The values of the dict are
            a list of strings that may be attached to each token if the 'file_upload' 
            argument exists.
            
            Args:
                :param iterable: The dictionary which determines how many tokens will be created. The values  are attached to each token
                :type iterable: dict
                :param id_append: Option to append the OBSID to each Token
                :type id_append: str
                :param key_name: The Token field which will hold the value of the dictionary's keys for each Token
                :type key_name: str
                :param file_upload: The name of the file which to upload to the tokens (typically srm.txt)
                :type file_upload: str

        """# TODO: Check if key_name is inside token_keys!
        for key in iterable:
            keys=dict(itertools.chain(self.token_keys.iteritems(),{key_name:str("%03d" % int(key) )}.iteritems()))
#            _=keys.pop('_attachments')
            pipeline=""
            if 'PIPELINE_STEP' in keys:
                pipeline="_"+keys['PIPELINE_STEP']
            token=self.th.create_token(keys,append=id_append+pipeline+"_"+id_prefix+str("%03d" % int(key) ))
            if file_upload:
                with open('temp_abn','w') as tmp_abn_file:
                    for i in iterable[key]:
                        tmp_abn_file.write("%s\n" % i)
                with open('temp_abn','r') as tmp_abn_file:
                   self.th.add_attachment(token,tmp_abn_file,file_upload)
                os.remove('temp_abn')
            self.__tokens.append(token)

    def add_attach_to_list(self,attachment,tok_list=None,name=None):
        '''Adds an attachment to all the tokens in the TokenSet, or to another list 
            of tokens if explicitly specified. 
        '''
        if not name: name=attachment
        if not tok_list: 
            tok_list=self.__tokens
        for token in tok_list:
            self.th.add_attachment(token, open(attachment,'r'),os.path.basename(name))

    @property
    def tokens(self):
        self.update_local_tokens()
        return self.__tokens

    def update_local_tokens(self):
        self.__tokens=[]
        self.th.load_views()
        for v in self.th.views.keys():
            if v!='overview_total':
                for t in self.th.list_tokens_from_view(v):
                    self.__tokens.append(t['id'])

    def add_keys_to_list(self,key,val,tok_list=None):
        if not tok_list:
            tok_list=self.__tokens
        to_update=[]
        for token in tok_list:
            document = self.th.db[token]
            document[key] = str(val)
            to_update.append(document)
        self.th.db.update(to_update)


