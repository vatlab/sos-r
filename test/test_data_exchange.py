#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.

from sos_notebook.test_utils import NotebookTest
import random


class TestDataExchange(NotebookTest):

    def _var_name(self):
        if not hasattr(self, '_var_idx'):
            self._var_idx = 0
        self._var_idx += 1
        return f'var{self._var_idx}'

    def get_from_SoS(self, notebook, sos_expr):
        var_name = self._var_name()
        notebook.call(f'{var_name} = {sos_expr}', kernel='SoS')
        return notebook.check_output(
            f'''\
            %get {var_name}
            {var_name}''',
            kernel='R')

    def put_to_SoS(self, notebook, r_expr):
        var_name = self._var_name()
        notebook.call(
            f'''\
            %put {var_name}
            {var_name} <- {r_expr}
            ''',
            kernel='R')
        return notebook.check_output(f'print(repr({var_name}))', kernel='SoS')

    def test_get_none(self, notebook):
        assert 'NULL' == self.get_from_SoS(notebook, 'None')

    def test_put_null(self, notebook):
        assert 'None' == self.put_to_SoS(notebook, 'NULL')

    def test_get_numpy_inf(self, notebook):
        notebook.call('import numpy', kernel='SoS')
        assert 'Inf' == self.get_from_SoS(notebook, 'numpy.inf')

    def test_put_inf(self, notebook):
        assert 'inf' == self.put_to_SoS(notebook, 'Inf')

    def test_get_int(self, notebook):
        assert '123' == self.get_from_SoS(notebook, '123')
        assert '1234567891234' == self.get_from_SoS(notebook, '1234567891234')
        # longer int does not gurantee precision any more, I am not sure
        # if the following observation will be consistent (784 vs 789)
        assert '123456789123456784' == self.get_from_SoS(
            notebook, '123456789123456789')

    def test_put_int(self, notebook):
        assert '123' == self.put_to_SoS(notebook, '123')
        assert '1234567891234' == self.put_to_SoS(notebook, '1234567891234')
        # longer int does not gurantee precision any more, I am not sure
        # if the following observation will be consistent (784 vs 789)
        assert '123456789123456784' == self.put_to_SoS(notebook,
                                                       '123456789123456789')

    def test_get_double(self, notebook):
        # FIXME: can we improve the precision here? Passing float as string
        # is certainly a bad idea.
        val = str(random.random())
        assert abs(float(val) - float(self.get_from_SoS(notebook, val))) < 1e-10

    def test_put_double(self, notebook):
        val = str(random.random())
        assert abs(float(val) - float(self.put_to_SoS(notebook, val))) < 1e-10

    def test_get_logic(self, notebook):
        assert 'TRUE' == self.get_from_SoS(notebook, 'True')
        assert 'FALSE' == self.get_from_SoS(notebook, 'False')

    def test_put_logic(self, notebook):
        assert 'True' == self.put_to_SoS(notebook, 'TRUE')
        assert 'False' == self.put_to_SoS(notebook, 'FALSE')

    def test_get_num_array(self, notebook):
        integers = [str(random.randint(1, 100000)) for x in range(10)]
        assert integers[0] == self.get_from_SoS(notebook, f'[{integers[0]}]')
        output = self.get_from_SoS(notebook, f"[{','.join(integers)}]")
        assert all(x in output for x in integers)
        #
        floats = ['1.34', '2.4']        
        assert floats[0] == self.get_from_SoS(notebook, f'[{floats[0]}]')
        output = self.get_from_SoS(notebook, f"[{','.join(floats)}]")
        assert all(x in output for x in floats)

    def test_put_num_array(self, notebook):
        integers = [str(random.randint(1, 100000)) for x in range(10)]
        assert integers[0] == self.put_to_SoS(notebook, f'c({integers[0]})')
        output = self.put_to_SoS(notebook, f'c({",".join(integers)})')
        assert all(x in output for x in integers)
        #
        floats = ['1232.43', '343.444', '90']
        assert floats[0] == self.put_to_SoS(notebook, f'c({floats[0]})')
        output = self.put_to_SoS(notebook, f'c({",".join(floats)})')
        assert all(x in output for x in floats)
        

    def test_get_logic_array(self, notebook):
        assert 'TRUE' == self.get_from_SoS(notebook, '[True]')
        output = self.get_from_SoS(notebook,
                                                      '[True, False, True]')
        assert output.count('TRUE') == 2                                                      
        assert output.count('FALSE') == 1

    def test_put_logic_array(self, notebook):
        # Note that single element numeric array is treated as single value
        assert 'True' == self.put_to_SoS(notebook, 'c(TRUE)')
        assert '[True, False, True]' == self.put_to_SoS(notebook,
                                                        'c(TRUE, FALSE, TRUE)')

    def test_get_str(self, notebook):
        assert "'ab c d'" == self.get_from_SoS(notebook, "'ab c d'")
        assert "'ab\\td'" == self.get_from_SoS(notebook, r"'ab\td'")

    def test_put_str(self, notebook):
        assert "'ab c d'" == self.put_to_SoS(notebook, "'ab c d'")
        assert "'ab\\td'" == self.put_to_SoS(notebook, r"'ab\td'")

    def test_get_mixed_list(self, notebook):
        assert "1.4\nTRUE\n'asd'" == self.get_from_SoS(notebook,
                                                       '[1.4, True, "asd"]')

    def test_put_mixed_list(self, notebook):
        # R does not have mixed list, it just convert everything to string.
        assert "['1.4', 'TRUE', 'asd']" == self.put_to_SoS(
            notebook, 'c(1.4, TRUE, "asd")')

    def test_get_dict(self, notebook):
        # Python does not have named ordered list, so get dictionary
        assert "$a\n1\n$b\n2\n$c\n'3'" == self.get_from_SoS(
            notebook, "dict(a=1, b=2, c='3')")

    def test_put_named_list(self, notebook):
        assert "{'a': 1, 'b': 2, 'c': '3'}" == self.put_to_SoS(
            notebook, "list(a=1, b=2, c='3')")

    def test_get_set(self, notebook):
        output = self.get_from_SoS(notebook, "{1.5, 'abc'}")
        assert "1.5\n'abc'" == output or "'abc'\n1.5" == output

    def test_put_unnamed_list(self, notebook):
        output = self.put_to_SoS(notebook, "list(1.5, 'abc')")
        assert "[1.5, 'abc']" == output or "['abc', 1.5]" == output

    def test_get_complex(self, notebook):
        assert "1+2.2i" == self.get_from_SoS(notebook, "complex(1, 2.2)")

    def test_put_complex(self, notebook):
        assert "(1+2.2j)" == self.put_to_SoS(notebook,
                                             "complex(real=1, imaginary=2.2)")

    def test_get_recursive(self, notebook):
        assert "$a\n1\n$b\n$c\n3\n$d\n'whatever'" == self.get_from_SoS(
            notebook, "{'a': 1, 'b': {'c': 3, 'd': 'whatever'}}")

    def test_put_recursive(self, notebook):
        assert "{'a': 1, 'b': {'c': 3, 'd': 'whatever'}}" == self.put_to_SoS(
            notebook, "list(a=1, b=list(c=3, d='whatever'))")

    def test_get_series(self, notebook):
        notebook.call('import pandas as pd', kernel='SoS')
        nums = [str(random.randint(1, 10000)) for x in range(10)]
        output = self.get_from_SoS(notebook, f'pd.Series([{",".join(nums)}])')
        for num in nums:
            assert num in output
        

    def test_put_series(self, notebook):
        output = self.put_to_SoS(notebook,
                                 "setNames(c(11, 22, 33), c('a', 'b', 'c'))")
        assert 'a    11' in output and 'b    22' in output and 'c    33' in output

    def test_get_matrix(self, notebook):
        notebook.call('import numpy as np', kernel='SoS')
        assert "0 1\n1 2\n3 4" in self.get_from_SoS(notebook,
                                                    'np.matrix([[1,2],[3,4]])')

    def test_put_matrix(self, notebook):
        output = self.put_to_SoS(notebook,
                                 "matrix(c(2, 4, 3, 1, 5, 7), nrow=2)")
        assert 'array' in output and '[2., 3., 5.]' in output and '[4., 1., 7.]' in output

    def test_get_dataframe(self, notebook):
        notebook.call(
            '''\
            %put df --to R
            import pandas as pd
            import numpy as np
            arr = np.random.randn(1000)
            arr[::10] = np.nan
            df = pd.DataFrame({'column_{0}'.format(i): arr for i in range(10)})
            ''',
            kernel='SoS')
        assert '1000' == notebook.check_output('dim(df)[1]', kernel='R')
        assert '10' == notebook.check_output('dim(df)[2]', kernel='R')

    def test_get_dataframe_bigint(self, notebook):
        notebook.call(
            '''\
            %put df --to R
            import pandas as pd
            import numpy as np
            df = pd.DataFrame(dict(a=[2147483648, 1], b=[2, 3]))
            ''',
            kernel='SoS',
            expect_error=False)
        assert '2147483648' in notebook.check_output('df[[1, 1]]', kernel='R')
        assert 'numeric' in notebook.check_output('class(df[[1]])', kernel='R')
        assert 'integer' in notebook.check_output('class(df[[2]])', kernel='R')

    def test_put_dataframe(self, notebook):
        notebook.call('%put mtcars', kernel='R')
        assert '32' == notebook.check_output('mtcars.shape[0]', kernel='SoS')
        assert '11' == notebook.check_output('mtcars.shape[1]', kernel='SoS')
        assert "'Mazda RX4'" == notebook.check_output(
            'mtcars.index[0]', kernel='SoS')

    def test_get_dict_with_special_keys(self, notebook):
        output = self.get_from_SoS(
            notebook, "{'11111': 1, '_1111': 'a', 11112: 2, (1,2): 3}")
        assert '$X11111' in output and '$X_1111' in output and '$X11112' in output and '$X_1__2_' in output
