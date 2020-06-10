#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.

import numpy
import pandas
import re
import tempfile

from collections import Sequence
from sos.utils import short_repr, env
from IPython.core.error import UsageError

from ._version import __version__


def homogeneous_type(seq):
    iseq = iter(seq)
    first_type = type(next(iseq))
    if first_type in (int, float):
        return True if all(isinstance(x, (int, float)) for x in iseq) else False
    else:
        return True if all(isinstance(x, first_type) for x in iseq) else False


# make the SoS dict key name to be valid in R list
def make_name(name):
    if name.isalpha():
        return name
    # the best way to detect an empty string is `if not {string}`
    if not name or not name[0].isalpha():
        name = 'X' + name
    return re.sub(r'\W', '_', name)


#
#  support for %get
#
#  Converting a Python object to a R expression that will be executed
#  by the R kernel.
#
#

# use dictionary to remove duplicated warnings
_R_repr_warnings = {}


def _R_repr(obj, processed=None):
    global _R_repr_warnings
    if isinstance(obj, bool):
        return 'TRUE' if obj else 'FALSE'
    elif isinstance(obj, (int, str)):
        return repr(obj)
    elif isinstance(obj, float):
        if numpy.isnan(obj):
            return 'NaN'
        elif numpy.isinf(obj):
            return 'Inf'
        else:
            return repr(obj)
    elif isinstance(obj, complex):
        return 'complex(real = ' + str(obj.real) + ', imaginary = ' + str(
            obj.imag) + ')'
    elif isinstance(obj, Sequence):
        if len(obj) == 0:
            return 'c()'
        # if the data is of homogeneous type, let us use c()
        # otherwise use list()
        # this can be confusion but list can be difficult to handle
        if homogeneous_type(obj):
            return 'c(' + ','.join(_R_repr(x) for x in obj) + ')'
        else:
            return 'list(' + ','.join(_R_repr(x) for x in obj) + ')'
    elif obj is None:
        return 'NULL'
    elif isinstance(obj, dict):
        if processed:
            if id(obj) in processed:
                return 'NULL'
        else:
            processed = set()
        processed.add(id(obj))
        return 'list(' + ','.join(
            '{}={}'.format(make_name(str(x)), _R_repr(y, processed))
            for x, y in obj.items()) + ')'
    elif isinstance(obj, set):
        return 'list(' + ','.join(_R_repr(x) for x in obj) + ')'
    elif isinstance(
            obj, (numpy.intc, numpy.intp, numpy.int8, numpy.int16, numpy.int32,
                  numpy.int64, numpy.uint8, numpy.uint16, numpy.uint32,
                  numpy.uint64, numpy.float16, numpy.float32, numpy.float64)):
        return repr(obj)
    elif isinstance(obj, numpy.matrixlib.defmatrix.matrix):
        try:
            import feather
        except ImportError:
            raise UsageError(
                'The feather-format module is required to pass numpy matrix as R matrix'
                'See https://github.com/wesm/feather/tree/master/python for details.'
            )
        feather_tmp_ = tempfile.NamedTemporaryFile(
            suffix='.feather', delete=False).name
        feather.write_dataframe(pandas.DataFrame(obj).copy(), feather_tmp_)
        return 'data.matrix(..read.feather({!r}))'.format(feather_tmp_)
    elif isinstance(obj, numpy.ndarray):
        if obj.ndim == 1:
            return 'array(c(' + ','.join(_R_repr(x) for x in obj) + '))'
        else:
            return 'array(' + 'c(' + ','.join(
                repr(x)
                for x in obj.swapaxes(obj.ndim - 2, obj.ndim - 1).flatten(
                    order='C')) + ')' + ', dim=(' + 'rev(c' + repr(
                        obj.swapaxes(obj.ndim - 2, obj.ndim - 1).shape) + ')))'
    elif isinstance(obj, pandas.DataFrame):
        try:
            import feather
        except ImportError:
            raise UsageError(
                'The feather-format module is required to pass pandas DataFrame as R data.frame'
                'See https://github.com/wesm/feather/tree/master/python for details.'
            )
        feather_tmp_ = tempfile.NamedTemporaryFile(
            suffix='.feather', delete=False).name
        try:
            data = obj.copy()
            # if the dataframe has index, it would not be transferred due to limitations
            # of feather. We will have to do something to save the index separately and
            # recreate it. (#397)
            if isinstance(data.index, pandas.Index):
                df_index = list(data.index)
                if len(df_index) != len(set(df_index)):
                    df_index = None
                    _R_repr_warnings[
                        'Index is ignored because R dataframe does not accept non-unique row names.'] = 1
            elif not isinstance(data.index, pandas.RangeIndex):
                # we should give a warning here
                df_index = None
            feather.write_dataframe(data, feather_tmp_)
        except Exception:
            # if data cannot be written, we try to manipulate data
            # frame to have consistent types and try again
            for c in data.columns:
                if not homogeneous_type(data[c]):
                    data[c] = [str(x) for x in data[c]]
            feather.write_dataframe(data, feather_tmp_)
            # use {!r} for path because the string might contain c:\ which needs to be
            # double quoted.
        return '..read.feather({!r}, index={})'.format(feather_tmp_,
                                                       _R_repr(df_index))
    elif isinstance(obj, pandas.Series):
        dat = list(obj.values)
        ind = list(obj.index.values)
        return 'setNames(' + 'c(' + ','.join(
            _R_repr(x) for x in dat) + ')' + ',c(' + ','.join(
                _R_repr(y) for y in ind) + '))'
    else:
        _R_repr_warnings[
            'Unsupported datatype {}. Variable is set to NULL'.format(
                short_repr(obj))] = 1
        return 'NULL'


# R    length (n)    Python
# NULL        None
# logical    1    boolean
# integer    1    integer
# numeric    1    double
# character    1    unicode
# logical    n > 1    array
# integer    n > 1    array
# numeric    n > 1    list
# character    n > 1    list
# list without names    n > 0    list
# list with names    n > 0    dict
# matrix    n > 0    array
# data.frame    n > 0    DataFrame

R_init_statements = r'''
..py.repr.logical.1 <- function(obj) {
    if(obj)
        'True'
    else
        'False'
}
..py.repr.integer.1 <- function(obj) {
    as.character(obj)
}
..py.repr.double.1 <- function(obj) {
    if (is.nan(obj)) {
      'numpy.nan'
    } else if (is.infinite(obj)) {
      'float("inf")'
    } else {
        as.character(obj)
    }
}
..py.repr.complex.1 <- function(obj) {
    rl = Re(obj)
    im = Im(obj)
    paste0('complex(', rl, ',', im, ')')
}
..py.repr.character.1 <- function(obj) {
    paste0('r"""', obj, '"""')
}
..has.row.names <- function(df) {
  !all(row.names(df)==seq(1, nrow(df)))
}
..py.repr.dataframe <- function(obj) {
    if (!require("arrow")) {
        install.packages('arrow', repos='https://cran.r-project.org')
        }
    library(arrow)
    tf = tempfile('arrow')
    write_feather(obj, tf)
    if (..has.row.names(obj)) {
        paste0("read_dataframe(r'", tf, "').set_index(pandas.Index(", ..py.repr(row.names(obj)),"))")
    } else {
        paste0("read_dataframe(r'", tf, "')")
    }
}
..py.repr.matrix <- function(obj) {
    if (!require("arrow")) {
        install.packages('arrow', repos='https://cran.r-project.org')
        }
    library(arrow)
    tf = tempfile('arrow')
    write_feather(as.data.frame(obj), tf)
    if (..has.row.names(obj)) {
        paste0("read_dataframe(r'", tf, "').set_index(pandas.Index(", ..py.repr(row.names(obj)),")).values")
    } else {
        paste0("read_dataframe(r'", tf, "').values")
    }
}
..py.repr.array.numer <- function(obj) {
    paste0("numpy.array(", "[", paste(obj, collapse = ","), "]).", paste0("reshape([",
                                                                        paste0(rev(dim(obj)), collapse = ","), "]).", paste0("swapaxes(",
                                                                                                                             length(dim(obj)) - 2, ",", length(dim(obj)) - 1, ")")))
}
..py.repr.array.char <- function(obj) {
    paste0("numpy.array(", "[", paste0( paste0("eval('", ..py.repr.character.1(obj), "')", collapse=',')), "]).", paste0("reshape([",
                                                                                                          paste0(rev(dim(obj)), collapse = ","), "]).", paste0("swapaxes(",
                                                                                                                                                               length(dim(obj)) - 2, ",", length(dim(obj)) - 1, ")")))
}
..py.repr.array.logical <- function(obj) {
  paste0("numpy.array(", "[", paste0( paste0("eval('", apply(obj,c(1:length(dim(obj))),..py.repr.logical.1), "')", collapse=',')), "]).", paste0("reshape([",
                                                                                                                     paste0(rev(dim(obj)), collapse = ","), "]).", paste0("swapaxes(",
                                                                                                                                                                          length(dim(obj)) - 2, ",", length(dim(obj)) - 1, ")")))
}
..py.repr.n <- function(obj) {
    paste("[",
        paste(sapply(obj, ..py.repr), collapse=','),
        "]")
}
..py.repr <- function(obj) {
    if (is.matrix(obj)) {
      ..py.repr.matrix(obj)
    } else if (is.data.frame(obj)) {
      ..py.repr.dataframe(obj)
    } else if (is.list(obj)) {
      # if the list has no name
      if (is.null(names(obj)))
        ..py.repr.n(obj)
      else {
        paste("dict([",
              paste(sapply(names(obj), function (x)
                paste0("(", shQuote(gsub("\\.", "_", as.character(x))), ",", ..py.repr(obj[[x]]), ")" )),
                collapse=','),
              "])")
        }
    } else if (is.array(obj)) {
      if (is.character(obj))
        ..py.repr.array.char(obj)
      else if (is.logical(obj))
        ..py.repr.array.logical(obj)
      else
        ..py.repr.array.numer(obj)
    } else if (is.null(obj)) {
      'None'
    } else if (is.integer(obj)) {
        # if the vector has no name
        if (is.null(names(obj)))
          if (length(obj) == 1)
            ..py.repr.integer.1(obj)
          else
            paste("[", paste(obj, collapse=','), "]")
        else
          paste0("pandas.Series(", "[", paste(unname(obj), collapse=','), "],", paste0("[", paste0(sapply(names(obj), ..py.repr.character.1), collapse=','), "]"), ")")
    } else if (is.complex(obj)) {
        # if the vector has no name
        if (is.null(names(obj)))
          if (length(obj) == 1)
            ..py.repr.complex.1(obj)
          else
            paste("[", paste(sapply(obj, ..py.repr.complex.1), collapse=','), "]")
        else
          paste0("pandas.Series(", "[", paste(sapply(unname(obj), ..py.repr.complex.1), collapse=','), "],", paste0("[", paste0(sapply(names(obj), ..py.repr.character.1), collapse=','), "]"), ")")
    } else if (is.double(obj)){
        if (is.null(names(obj))) {
          if (length(obj) == 1) {
            ..py.repr.double.1(obj)
          } else {
            paste("[", paste(sapply(obj, ..py.repr.double.1), collapse=','), "]")
          }
        } else {
          paste0("pandas.Series(", "[", paste(unname(obj), collapse=','), "],", paste0("[", paste0(sapply(names(obj), ..py.repr.character.1), collapse=','), "]"), ")")
        }
    } else if (is.character(obj)) {
        # if the vector has no name
        if (is.null(names(obj)))
          if (length(obj) == 1)
            ..py.repr.character.1(obj)
          else
            paste("[", paste(sapply(obj, ..py.repr.character.1), collapse=','), "]")
        else
          paste0("pandas.Series(", "[", paste(sapply(unname(obj), ..py.repr.character.1), collapse=','), "],", paste0("[", paste0(sapply(names(obj), ..py.repr.character.1), collapse=','), "]"), ")")
    } else if (is.logical(obj)) {
      # if the vector has no name
        if (is.na(obj)) {
            'numpy.nan'
        } else if (is.null(names(obj)))
          if (length(obj) == 1)
            ..py.repr.logical.1(obj)
          else
            ..py.repr.n(obj)
        else
          paste0("pandas.Series(", "[", paste(sapply(unname(obj), ..py.repr.logical.1), collapse=','), "],", paste0("[", paste0(sapply(names(obj), ..py.repr.character.1), collapse=','), "]"), ")")
    } else {
      "'Untransferrable variable'"
    }
}
..read.feather <- function(filename, index=NULL) {
    if (! suppressMessages(suppressWarnings(require("arrow", quietly = TRUE)))) {
      try(install.packages('arrow', repos='https://cran.r-project.org'), silent=TRUE)
      if (!suppressMessages(suppressWarnings(require("arrow"))))
        stop('Failed to install arrow library')
    }
    suppressPackageStartupMessages(library(arrow, quietly = TRUE))
    data = as.data.frame(read_feather(filename))
    if (!is.null(index))
      rownames(data) <- index
    for (cn in names(data)[sapply(data,is, class2="integer64")]) {
      data[[cn]] <- tryCatch( {
          as.integer(data[[cn]])
      }, warning = function (w) {
          message("out of range integer column is converted to numeric")
          as.numeric(data[[cn]])
      }
    )
    }
    return(data)
}
..sos.preview <- function(name) {
    tryCatch( str(get(name)), error = function(err) { cat(paste('Unknown variable', name)) })
}
..sos.expand <- function(text, sigil) {
    if (! suppressMessages(suppressWarnings(require("knitr", quietly = TRUE)))) {
      try(install.packages('knitr', repos='https://cran.r-project.org'), silent=TRUE)
      if (!suppressMessages(suppressWarnings(require("knitr"))))
        stop('Failed to install knitr library')
    }
    suppressPackageStartupMessages(library(knitr, quietly = TRUE))
    cat(knit_expand(text=text, delim=sigil))
}
'''


class sos_R:
    background_color = '#DCDCDA'
    supported_kernels = {'R': ['ir']}
    options = {'assignment_pattern': r'^\s*([_A-Za-z0-9\.]+)\s*(=|<-).*$'}
    cd_command = 'setwd({dir!r})'
    __version__ = __version__

    def __init__(self, sos_kernel, kernel_name='ir'):
        self.sos_kernel = sos_kernel
        self.kernel_name = kernel_name
        self.init_statements = R_init_statements

    def get_vars(self, names):
        global _R_repr_warnings
        for name in names:
            if name.startswith('_'):
                self.sos_kernel.warn(
                    f'Variable {name} is passed from SoS to kernel {self.kernel_name} as {"." + name[1:]}'
                )
                newname = '.' + name[1:]
            else:
                newname = name
            _R_repr_warnings = {}
            r_repr = _R_repr(env.sos_dict[name])
            if _R_repr_warnings:
                self.sos_kernel.warn('\n'.join(_R_repr_warnings.keys()))
                _R_repr_warnings = {}
            env.log_to_file('VARIABLE', r_repr)
            self.sos_kernel.run_cell(
                f'{newname} <- {r_repr}',
                True,
                False,
                on_error=f'Failed to get variable {name} to R')

    def put_vars(self, items, to_kernel=None):
        # first let us get all variables with names starting with sos
        response = self.sos_kernel.get_response(
            'cat(..py.repr(ls()))', ('stream',), name=('stdout',))[0][1]
        all_vars = eval(response['text'])
        all_vars = [all_vars] if isinstance(all_vars, str) else all_vars

        items += [x for x in all_vars if x.startswith('sos')]

        for item in items:
            if '.' in item:
                self.sos_kernel.warn(
                    f'Variable {item} is put to SoS as {item.replace(".", "_")}'
                )

        if not items:
            return {}

        py_repr = f'cat(..py.repr(list({",".join("{0}={0}".format(x) for x in items)})))'
        response = self.sos_kernel.get_response(
            py_repr, ('stream',), name=('stdout',))[0][1]
        expr = response['text']

        if to_kernel in ('Python2', 'Python3'):
            # directly to python3
            return '{}\n{}\n{}\nglobals().update({})'.format(
                'from feather import read_dataframe\n'
                if 'read_dataframe' in expr else '',
                'import numpy' if 'numpy' in expr else '',
                'import pandas' if 'pandas' in expr else '', expr)
        # to sos or any other kernel
        else:
            # irkernel (since the new version) does not produce execute_result, only
            # display_data
            try:
                if 'read_dataframe' in expr:
                    # imported to be used by eval
                    from feather import read_dataframe
                    # suppress flakes warning
                    assert read_dataframe
                # evaluate as raw string to correctly handle \\ etc
                return eval(expr)
            except Exception as e:
                self.sos_kernel.warn(f'Failed to evaluate {expr!r}: {e}')
                return None

    def expand(self, text, sigil):
        if '"' in sigil:
            self.sos_kernel.warn(f'Unacceptable delimiter {sigil}')
            return text
        try:
            text = text.replace('"', r'\"')
            l, r = sigil.split(' ')
            # in the case of "`r", we actually use "`r " as left delimiter.
            if l[-1].isalpha():
                l = l + ' '
            if r[0].isalpha():
                r = ' ' + r
            return self.sos_kernel.get_response(
                f'..sos.expand("{text}", c("{l}", "{r}"))', ('stream',),
                name=('stdout',))[0][1]['text']
        except Exception:
            err_msg = self.sos_kernel.get_response(
                f'..sos.expand("{text}", c("{l}", "{r}"))', ('error',),
                name=('evalue',))[0][1]['evalue']
            self.sos_kernel.warn(
                f'Failed to expand {text} with sigil {sigil}: {err_msg}')
            return text

    def preview(self, item):
        # return the preview of variable.
        try:
            return "", self.sos_kernel.get_response(
                f'..sos.preview("{item}")', ('stream',),
                name=('stdout',))[0][1]['text']
        except Exception as e:
            env.log_to_file('VARIABLE', f'Preview of {item} failed: {e}')
            return None

    def sessioninfo(self):
        response = self.sos_kernel.get_response(
            r'cat(paste(capture.output(sessionInfo()), collapse="\n"))',
            ('stream',),
            name=('stdout',))[0]
        return response[1]['text']
