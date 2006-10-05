# helper classes for git-buildpackge and friends
# (C) 2006 Guido Guenther <agx@sigxcpu.org>

import subprocess
import sys

class CommandExecFailed(Exception):
    pass

class Command(object):
    verbose=False

    def __init__(self, cmd, args=[]):
        self.cmd=cmd
        self.args=args
        self.run_error="Couldn't run '%s %s'" % (cmd," ".join(args))

    def __run(self, args):
        try:
            if self.verbose:
                print self.cmd, self.args, args
            retcode = subprocess.call([self.cmd]+self.args+args)
            if retcode < 0:
                print >>sys.stderr, "%s was terminated by signal %d" % (self.cmd,  -retcode)
            elif retcode > 0:
                print >>sys.stderr, "%s returned %d" % (self.cmd,  retcode)
        except OSError, e:
            print >>sys.stderr, "Execution failed:", e
            retcode=1
        if retcode:
            print >>sys.stderr,self.run_error
        return retcode

    def __call__(self, args=[]):
        if self.__run(args):
            raise CommandExecFailed


class UnpackTGZ(Command):
    def __init__(self, tgz, dir):
        self.tgz=tgz
        self.dir=dir
        Command.__init__(self, 'tar', [ '-C', dir, '-zxf', tgz ])
        self.run_error="Couldn't unpack %s" % (self.tgz,)


class RemoveTree(Command):
    "Remove a whole directory tree"
    def __init__(self, tree):
        self.tree=tree
        Command.__init__(self, 'rm', [ '-rf', tree ])
        self.run_error="Couldn't remove %s" % (self.tree,)


class Dch(Command):
    def __init__(self, version, msg):
        args=['-v', version]
        if msg:
            args.append(msg)
        Command.__init__(self, 'dch', args)
        self.run_error="Dch failed."


class DpkgSourceExtract(Command):
    def __init__(self):
        Command.__init__(self, 'dpkg-source', ['-x'])
    
    def __call__(self, dsc, output_dir):
        self.run_error="Couldn't extract %s" % (dsc,)
        Command.__call__(self, [dsc, output_dir])


class GitLoadDirs(Command):
    def __init__(self):
        Command.__init__(self, 'git_load_dirs')

    def __call__(self, dir, log=''):
        self.dir=dir
        self.run_error="Couldn't import %s" % self.dir
        args=[ [],['-L', log] ] [len(log) > 0]
        Command.__call__(self, args+[dir])


class GitCommand(Command):
    "Mother/Father of all git commands"
    def __init__(self, cmd, args=[]):
        Command.__init__(self, 'git-'+cmd, args)


class GitInitDB(GitCommand):
    def __init__(self):
        GitCommand.__init__(self,'init-db')
        self.run_error="Couldn't init git repository"


class GitShowBranch(GitCommand):
    def __init__(self):
        GitCommand.__init__(self,'branch')
        self.run_error="Couldn't list branches"


class GitBranch(GitCommand):
    def __init__(self):
        GitCommand.__init__(self,'branch')

    def __call__(self, branch):
        self.run_error="Couldn't create branch %s" % (branch,)
        GitCommand.__call__(self, [branch])


class GitCheckoutBranch(GitCommand):
    def __init__(self, branch):
        GitCommand.__init__(self,'checkout', [branch])
        self.branch=branch
        self.run_error="Couldn't switch to %s branch" % self.branch


class GitPull(GitCommand):
    def __init__(self, repo, branch):
        GitCommand.__init__(self,'pull', [repo, branch]) 
        self.run_error="Couldn't pull %s to %s" % (branch, repo)


class GitTag(GitCommand):
    def __init__(self):
        GitCommand.__init__(self,'tag') 

    def __call__(self, tag):
        self.run_error="Couldn't tag %s" % (tag,)
        GitCommand.__call__(self, [tag])


class GitAdd(GitCommand):
    """add a lists of files"""
    def __init__(self):
        GitCommand.__init__(self,'add')
        self.run_error="Couldn't add files"


class GitCommitAll(GitCommand):
    """Commit files to the repository"""
    def __init__(self):
        GitCommand.__init__(self,'commit', ['-a'])

    def __call__(self, msg=''):
        args = [ [], ['-m', msg] ][len(msg) > 0]
        self.run_error="Couldn't commit -a %s" % " ".join(args)
        GitCommand.__call__(self, args)


# vim:et:ts=4:sw=4: