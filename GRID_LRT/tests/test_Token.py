from GRID_LRT import Token 
from GRID_LRT.get_picas_credentials import picas_cred
import os
import glob
import unittest
import sys

vers=str(sys.version_info[0])+"."+str(sys.version_info[1])
T_TYPE="travis_ci_test"+vers
TOKEN="travis_getSBX_test"+vers


class TokenTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_Token(self):
        pc = picas_cred()
        th = Token.Token_Handler(t_type=T_TYPE, uname=pc.user, pwd=pc.password, dbn='sksp_unittest')
        self.assertTrue(th.get_db(uname=pc.user, pwd=pc.password,  dbn='sksp_unittest', 
                        srv="https://picas-lofar.grid.surfsara.nl:6984").name == 'sksp_unittest')
        th.create_token(keys={'test_suite':'Token'}, append="Tokentest", attach=[])
        th.add_status_views()
        th.add_overview_view()
        th.load_views()
        views = th.views

        