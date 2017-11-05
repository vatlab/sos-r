#!/usr/bin/env python3
#
# This file is part of Script of Scripts (SoS), a workflow system
# for the execution of commands and scripts in different languages.
# Please visit https://github.com/vatlab/SOS for more information.
#
# Copyright (C) 2016 Bo Peng (bpeng@mdanderson.org)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import unittest
from ipykernel.tests.utils import execute, wait_for_idle
from sos_notebook.test_utils import sos_kernel, get_display_data, get_std_output

class TestSoSMagics(unittest.TestCase):

    def testMagicShutdown(self):
        with sos_kernel() as kc:
            iopub = kc.iopub_channel
            execute(kc=kc, code='''
%use R
a = 100
cat(a)
''')
            stdout, stderr = get_std_output(iopub)
            self.assertTrue(stdout.endswith('100'), 'Should have output {}'.format(stdout))
            #self.assertEqual(stderr, '')
            #now let us restart
            execute(kc=kc, code='''
%shutdown --restart R
%use R
cat(a)
''')
            stdout, _ = get_std_output(iopub)
            # not sure what is going on
            self.assertEqual(stdout, '')
            execute(kc=kc, code='%use SoS')
            wait_for_idle(kc)

    def testMagicPreview(self):
        with sos_kernel() as kc:
            iopub = kc.iopub_channel
            #
            execute(kc=kc, code='''
%preview mtcars
%use R
''')
            wait_for_idle(kc)
            execute(kc=kc, code='''
%use SoS
''')
            wait_for_idle(kc)
            # preview figure
            execute(kc=kc, code='''
%preview -n a.png
R:
    png('a.png')
    plot(0)
    dev.off()
''')
            res = get_display_data(iopub, 'image/png')
            self.assertGreater(len(res), 1000, 'Expect a image {}'.format(res))
            # preview jpg
            execute(kc=kc, code='''
%preview a.jp*
R:
    jpeg('a.jpg')
    plot(0)
    dev.off()
''')
            res = get_display_data(iopub, 'image/jpeg')
            self.assertGreater(len(res), 1000, 'Expect a image {}'.format(res))
            # preview pdf in iframe (by default)
            execute(kc=kc, code='''
%preview a.pdf
R:
    pdf('a.pdf')
    plot(0)
    dev.off()
''')
            # or png (which requires imagemagick
            wait_for_idle(kc)
            execute(kc=kc, code='''
%preview a.pdf -s png
''')
            # could return html or image depending on configuration
            res = get_display_data(iopub, ('text/html', 'image/png'))
            self.assertTrue('iframe' in res or len(res) > 1000, 'Expect a image {}'.format(res))
            #
            # switch back
            execute(kc=kc, code='%use SoS')
            wait_for_idle(kc)


    def testVisualizer(self):
        with sos_kernel() as kc:
            # preview variable
            iopub = kc.iopub_channel
            # preview dataframe
            execute(kc=kc, code='''
%preview mtcars -n -l 10
%get mtcars --from R
''')
            res = get_display_data(iopub, 'text/html')
            self.assertTrue('dataframe_container' in res and 'Mazda' in res, 'Expect preview {}'.format(res))
            #
            execute(kc=kc, code='''
%preview mtcars -n -s scatterplot mpg disp --by cyl
%get mtcars --from R
''')
            res = get_display_data(iopub, 'text/html')
            self.assertTrue('Hornet' in res, 'Expect preview {}'.format(res))
            #
            execute(kc=kc, code='''
%preview mtcars -n -s scatterplot _index disp hp mpg --tooltip wt qsec
%get mtcars --from R
''')
            res = get_display_data(iopub, 'text/html')
            self.assertTrue('Hornet' in res, 'Expect preview {}'.format(res))
            #
            execute(kc=kc, code='''
%preview mtcars -n -s scatterplot disp hp --log xy --xlim 60 80 --ylim 40 300
%get mtcars --from R
''')
            res = get_display_data(iopub, 'text/html')
            self.assertTrue('Hornet' in res, 'Expect preview {}'.format(res))


if __name__ == '__main__':
    unittest.main()
