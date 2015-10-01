# vim: set fileencoding=utf-8 :
#
# (C) 2006-2011 Guido Guenther <agx@sigxcpu.org>
# (C) 2012 Intel Corporation <markus.lehtonen@linux.intel.com>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, please see
#    <http://www.gnu.org/licenses/>
#
"""Common functionality for Debian and RPM buildpackage scripts"""

import os, os.path
import pipes
import tempfile
import shutil
from gbp.command_wrappers import (CatenateTarArchive)
from gbp.errors import GbpError
import gbp.log

# when we want to reference the index in a treeish context we call it:
index_name = "INDEX"
# when we want to reference the working copy in treeish context we call it:
wc_name = "WC"
# index file name used to export working copy
wc_index = ".git/gbp_index"


def sanitize_prefix(prefix):
    """
    Sanitize the prefix used for generating source archives

    >>> sanitize_prefix('')
    '/'
    >>> sanitize_prefix('foo/')
    'foo/'
    >>> sanitize_prefix('/foo/bar')
    'foo/bar/'
    """
    if prefix:
        return prefix.strip('/') + '/'
    return '/'


def git_archive_submodules(repo, treeish, output, prefix, comp_type, comp_level, comp_opts):
    """
    Create tar.gz of an archive with submodules

    since git-archive always writes an end of tarfile trailer we concatenate
    the generated archives using tar and compress the result.

    Exception handling is left to the caller.
    """
    prefix = sanitize_prefix(prefix)
    tarfile = output.rsplit('.', 1)[0]
    tempdir = tempfile.mkdtemp()
    submodule_tarfile = os.path.join(tempdir, "submodule.tar")
    try:
        # generate main tarfile
        repo.archive(format='tar', prefix=prefix,
                     output=tarfile, treeish=treeish)

        # generate each submodule's tarfile and append it to the main archive
        for (subdir, commit) in repo.get_submodules(treeish):
            tarpath = [subdir, subdir[2:]][subdir.startswith("./")]

            gbp.log.debug("Processing submodule %s (%s)" % (subdir, commit[0:8]))
            repo.archive(format='tar', prefix='%s%s/' % (prefix, tarpath),
                         output=submodule_tarfile, treeish=commit, cwd=subdir)
            CatenateTarArchive(tarfile)(submodule_tarfile)

        # compress the output
        ret = os.system("%s -%s %s %s" % (comp_type, comp_level, comp_opts, tarfile))
        if ret:
            raise GbpError("Error creating %s: %d" % (output, ret))
    finally:
        shutil.rmtree(tempdir)


def git_archive_single(treeish, output, prefix, comp_type, comp_level, comp_opts):
    """
    Create tar.gz of an archive without submodules

    Exception handling is left to the caller.
    """
    prefix = sanitize_prefix(prefix)
    pipe = pipes.Template()
    pipe.prepend("git archive --format=tar --prefix=%s %s" % (prefix, treeish), '.-')
    pipe.append('%s -c -%s %s' % (comp_type, comp_level, comp_opts),  '--')
    ret = pipe.copy('', output)
    if ret:
        raise GbpError("Error creating %s: %d" % (output, ret))


#{ Functions to handle export-dir
def dump_tree(repo, export_dir, treeish, with_submodules, recursive=True):
    "dump a tree to output_dir"
    output_dir = os.path.dirname(export_dir)
    prefix = sanitize_prefix(os.path.basename(export_dir))
    if recursive:
        paths = []
    else:
        paths = ["'%s'" % nam for _mod, typ, _sha, nam in
                    repo.list_tree(treeish) if typ == 'blob']

    pipe = pipes.Template()
    pipe.prepend('git archive --format=tar --prefix=%s %s -- %s' %
                 (prefix, treeish, ' '.join(paths)), '.-')
    pipe.append('tar -C %s -xf -' % pipes.quote(output_dir), '-.')
    top = os.path.abspath(os.path.curdir)
    try:
        ret = pipe.copy('', '')
        if ret:
            raise GbpError("Error in dump_tree archive pipe")

        if recursive and with_submodules:
            if repo.has_submodules():
                repo.update_submodules()
            for (subdir, commit) in repo.get_submodules(treeish):
                gbp.log.info("Processing submodule %s (%s)" % (subdir, commit[0:8]))
                tarpath = [subdir, subdir[2:]][subdir.startswith("./")]
                os.chdir(subdir)
                pipe = pipes.Template()
                pipe.prepend('git archive --format=tar --prefix=%s%s/ %s' %
                             (prefix, tarpath, commit), '.-')
                pipe.append('tar -C %s -xf -' % pipes.quote(output_dir),  '-.')
                ret = pipe.copy('', '')
                os.chdir(top)
                if ret:
                     raise GbpError("Error in dump_tree archive pipe in submodule %s" % subdir)
    except OSError as err:
        gbp.log.err("Error dumping tree to %s: %s" % (output_dir, err[0]))
        return False
    except GbpError as err:
        gbp.log.err(err)
        return False
    except Exception as e:
        gbp.log.err("Error dumping tree to %s: %s" % (output_dir, e))
        return False
    finally:
        os.chdir(top)
    return True


def write_wc(repo, force=True):
    """write out the current working copy as a treeish object"""
    repo.add_files(repo.path, force=force, index_file=wc_index)
    tree = repo.write_tree(index_file=wc_index)
    return tree


def drop_index():
    """drop our custom index"""
    if os.path.exists(wc_index):
        os.unlink(wc_index)
