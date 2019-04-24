#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.

import pytest
import os
import sys
import tempfile
from textwrap import dedent
from sos_notebook.test_utils import NotebookTest

class TestInterface(NotebookTest):

    def test_prompt_color(self, notebook):
        '''test color of input and output prompt'''
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            cat('this is R')
            '''), kernel="R")
        assert all([a == b] for a, b in zip([86, 86, 85],
                                            notebook.get_input_backgroundColor(idx)))
        assert all([a == b] for a, b in zip([86, 86, 85],
                                            notebook.get_output_backgroundColor(idx)))

    def test_cd(self, notebook):
        '''Support for change of directory with magic %cd'''
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            getwd()
            '''), kernel="R")
        output1 = notebook.get_cell_output(index=idx)
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            %cd ..
            '''), kernel="SoS")
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            getwd()
            '''), kernel="R")
        output2 = notebook.get_cell_output(index=idx)
        assert len(output1) > len(output2)
        assert output1.strip("'").startswith(output2.strip("'"))
        #
        # cd to a specific directory
        tmpdir = os.path.join(tempfile.gettempdir(), 'somedir')
        os.makedirs(tmpdir, exist_ok=True)
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent(f'''\
            %cd {tmpdir}
            '''), kernel="SoS")
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            cat(getwd())
            '''), kernel="R")
        output3 = notebook.get_cell_output(index=idx)
        assert os.path.realpath(tmpdir) == os.path.realpath(output3)

    def test_get(self, notebook):
        '''Test get variables with strange names'''
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            _a = 5
            '''), kernel="SoS")
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            _a = 5
            '''), kernel="R")

    def test_put(self, notebook):
        '''Test put variables with strange names'''

    def test_preview(self, notebook):
        '''Test support for %preview'''
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            %preview -n var
            var = seq(1, 1000)
            '''), kernel="R")
        output = notebook.get_cell_output(index=idx)
        # in a normal var output, 100 would be printed. The preview version would show
        # type and some of the items in the format of
        #   int [1:1000] 1 2 3 4 5 6 7 8 9 10 ...
        assert 'int' in output and '3' in output and '9' in output and '111' not in output
        #
        # return 'Unknown variable' for unknown variable
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            %preview -n unknown_var
            '''), kernel="R")
        assert 'Unknown variable' in notebook.get_cell_output(index=idx)
        #
        # return 'Unknown variable for expression
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            %preview -n var[1]
            '''), kernel="R")
        assert 'Unknown variable' in notebook.get_cell_output(index=idx)

    def test_sessioninfo(self, notebook):
        '''test support for %sessioninfo'''
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            cat('this is R')
            '''), kernel="R")
        idx = notebook.append_and_execute_cell_in_kernel(content=dedent('''\
            %sessioninfo
            '''), kernel="SoS")
        assert 'R version' in notebook.get_cell_output(index=idx)
