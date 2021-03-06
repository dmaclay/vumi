from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import exists
from datetime import datetime
from os.path import join as _join
from os import walk
import re

from springfield.deploy.utils import git, system, base, twistd

RELEASE_NAME_FORMAT = '%Y%m%d_%H%M%S' # timestamped
# default for now
env.hosts = ['ubuntu@vumi.praekeltfoundation.org']

def _setup_env(fn):
    def wrapper(branch, *args, **kwargs):
        layout(branch)
        return fn(branch, *args, **kwargs)
    wrapper.func_name = fn.func_name
    wrapper.func_doc = (fn.func_doc or '') + \
                                        "Requires the branch from which you " \
                                        "want to deploy as an argument."
    return wrapper


def _setup_env_for(branch):
    env.branch = branch
    env.github_repo = 'http://github.com/%(github_user)s/%(github_repo_name)s.git' % env
    env.deploy_to = '/var/praekelt/%(github_repo_name)s/%(branch)s' % env
    env.releases_path = "%(deploy_to)s/releases" % env
    env.current = "%(deploy_to)s/current" % env
    env.shared_path = "%(deploy_to)s/shared" % env
    env.tmp_path = "%(shared_path)s/tmp" % env
    env.pip_cache_path = "%(tmp_path)s/cache/pip" % env
    env.pids_path = "%(tmp_path)s/pids" % env
    env.logs_path = "%(shared_path)s/logs" % env
    env.repo_path = "%(shared_path)s/repositories" % env
    env.django_settings_file = "environments.%(branch)s" % env
    env.layout = [
        env.releases_path,
        env.tmp_path,
        env.pip_cache_path,
        env.pids_path,
        env.logs_path,
        env.repo_path,
    ]

def _repo_path(repo_name):
    return '%(repo_path)s/%(github_repo_name)s' % env

def _repo(repo_name):
    """helper to quickly switch to a repository"""
    return cd(_repo_path(repo_name))

def layout(branch):
    """
    Create a file system directory layout for deploying to.
    """
    require('hosts')
    _setup_env_for(branch)
    require('layout', provided_by=['_setup_env_for'])
    system.create_dirs(env.layout)


@_setup_env
def redeploy(branch):
    """
    Shutdown then deploy
    Don't use this on initial deploy
    """
    shutdown(branch)
    deploy(branch)


@_setup_env
def deploy(branch):
    """
    Deploy the application in a timestamped release folder.
    
        $ fab deploy:staging
    
    Internally this does the following:
    
        * `git pull` if a cached repository already exists
        * `git clone` if it's the first deploy ever
        * Checkout the current selected branch
        * Create a new timestamped release directory
        * Copy the cached repository to the new release directory
        * Setup the virtualenv
        * Install PIP's requirements, downloading new ones if not already cached
        * Symlink `<branch>/current` to `<branch>/releases/<timestamped release directory>`
    
    """
    if not git.is_repository(_repo_path(env.github_repo_name)):
        # repository doesn't exist, do a fresh clone
        with cd(env.repo_path):
            git.clone(env.github_repo, env.github_repo_name)
        with _repo(env.github_repo_name):
            git.checkout(branch)
    else:
        # repository exists
        with _repo(env.github_repo_name):
            if not (branch == git.current_branch()):
                # switch to our branch if not already
                git.checkout(branch)
            # pull in the latest code
            git.pull(branch)
    # 20100603_125848
    new_release_name = datetime.utcnow().strftime(RELEASE_NAME_FORMAT)
    # /var/praekelt/vumi/staging/releases/20100603_125848
    new_release_path = _join(env.releases_path, new_release_name)
    # /var/praekelt/vumi/staging/releases/20100603_125848/vumi
    # Django needs the project name as it's parent dir since that is 
    # automagically appended to the loadpath
    new_release_repo = _join(new_release_path, env.github_repo_name)
    
    system.create_dir(new_release_path)
    system.copy_dirs(_repo_path(env.github_repo_name), new_release_path)
    
    copy_settings_file(branch, release=new_release_name)
    
    symlink_shared_dirs = ['logs', 'tmp']
    for dirname in symlink_shared_dirs:
        with cd(new_release_repo):
            system.remove(dirname, recursive_force=True)
            system.symlink(_join(env.shared_path, dirname), dirname)
    
    # create the virtualenv
    create_virtualenv(branch)
    # ensure we're deploying the exact revision as we locally have
    base.set_current(new_release_name)


@_setup_env
def copy_settings_file(branch, release=None):
    """
    Copy the settings file for this branch to the server
    
        $ fab copy_settings_file:staging
        
    If no release is specified it defaults to the latest release.
    
    
    """
    release = release or base.current_release()
    directory = _join(env.releases_path, release, env.github_repo_name)
    put(
        "environments/%(branch)s.py" % env, 
        _join(directory, "environments/%(branch)s.py" % env)
    )


def fabdir(branch, release=None):
    """
    Copy everything in fab/<branch>/ to the server
    i.e.
        local:  vumi/fab/staging/config/test_smpp.yaml
        would be copied to
        remote: vumi/config/test_smpp.yaml

    Optionally specify a partial filepath in addition to the branch
    i.e.
        $ fab -c fabric.config fabdir:staging/con
        might only copy:
            fab/staging/config/test.txt
            and
            fab/staging/confidential/pass.cfg
            not the rest of fab/staging
        and
        $ fab -c fabric.config fabdir:staging/config/test.txt
        would only copy that file

    'Hidden' diretories (prefixed with a dot like .mydir)
    will be ignored when they are immediately within fab/<branch>/
    unless the full 'hidden' directory name is included after <branch>
    when invoking fabdir, in which case the 'hidden' dir will be trimmed off
    along with fab/<branch>/ before copying to the remote directory.
    i.e.
        $ fab -c fabric.config fabdir:staging
        or
        $ fab -c fabric.config fabdir:staging/.myd
        will both ignore:
            fab/staging/.mydir
        but
        $ fab -c fabric.config fabdir:staging/.mydir
        or
        $ fab -c fabric.config fabdir:staging/.mydir/te
        would copy
        local: vumi/fab/staging/.mydir/tests/test.txt
        to
        remote: vumi/tests/test.txt

    This makes it easy to maintain multiple config directories
    each with files of the same name for a given branch
    i.e.
        fab/staging/.clickatell/config/smpp.yaml
        vs
        fab/staging/.safaricom/config/smpp.yaml
    so files in github like supervisord.staging.conf can remain unchanged
    """
    paths = re.match('(?P<branch>[^/]*)/?(?P<filepath>.*)',branch).groupdict()
    __fabdir(paths['branch'], paths['filepath'], release)

@_setup_env
def __fabdir(branch, filepath='', release=None):
    # only a function taking the split up branch/filepath can be decorated
    release = release or base.current_release()
    directory = _join(env.releases_path, release, env.github_repo_name)

    for root, dirs, files in walk("fab/%s" % branch):
        subdir = re.sub("^fab/%s/?" % branch,'',root)
        for name in dirs:
            joinpath = _join(subdir, name)
            # only make the dirs you need
            if re.match(re.escape(filepath), joinpath) \
            or re.match(re.escape(joinpath)+'/', filepath):
                if joinpath[0:1]!='.' \
                or joinpath.split('/')[0] == filepath.split('/')[0]:
                    # ignore or trim 'hidden' dirs in fab/<branch>/
                    run("mkdir -p %s" %  _join(directory, re.sub('^\.[^/]*/?', '', joinpath)))
        for name in files:
            joinpath = _join(subdir, name)
            if filepath == '' or re.match(re.escape(filepath), joinpath):
                if joinpath[0:1]!='.' \
                or joinpath.split('/')[0] == filepath.split('/')[0] \
                or subdir == '':
                    # ignore or trim filepaths within 'hidden' dirs in fab/<branch>/
                    put(_join(root, name),
                        _join(directory, re.sub('^\.[^/]*/', '', joinpath)))


@_setup_env
def managepy(branch, command, release=None):
    """
    Execute a ./manage.py command in the virtualenv with the current
    settings file
    
        $ fab managepy:staging,"syncdb"
    
    This will do a `./manage.py syncdb --settings=environments.staging`
    within the virtualenv.
    
    If no release is specified it defaults to the latest release.
    
    """
    return execute(branch, "./manage.py %s --settings=%s" % (
        command, 
        env.django_settings_file
    ), release)

@_setup_env
def execute(branch, command, release=None):
    """
    Execute a shell command in the virtualenv
    
        $ fab execute:staging,"tail logs/*.log"
    
    If no release is specified it defaults to the latest release.
    
    """
    release = release or base.current_release()
    directory = _join(env.releases_path, release, env.github_repo_name)
    return _virtualenv(directory, command)

@_setup_env
def create_virtualenv(branch, release=None):
    """
    Create the virtualenv and install the PIP requirements
    
        $ fab create_virtualenv:staging
    
    If no release is specified it defaults to the latest release
    
    """
    release = release or base.current_release()
    directory = _join(env.releases_path, release, env.github_repo_name)
    with cd(directory):
        return run(" && ".join([
            "virtualenv --no-site-packages ve",
            "source ve/bin/activate",
            "pip -E ve install --download-cache=%(pip_cache_path)s -r config/requirements.pip" % env,
            "python setup.py develop",
        ]))


def _virtualenv(directory, command, env_name='ve'):
    activate = 'source %s/bin/activate' % env_name
    deactivate = 'deactivate'
    with cd(directory):
        run(' && '.join([activate, command, deactivate]))


@_setup_env
def update(branch):
    """
    Pull in the latest code for the latest release.
    
        $ fab update:staging
        
    Only to be used for small fixed, typos etc..

    Runs git stash first to undo fabdir effects
    """
    current_release = base.releases(env.releases_path)[-1]
    copy_settings_file(branch, release=current_release)
    with cd(_join(env.current, env.github_repo_name)):
        run("git stash")
        git.pull(branch)


@_setup_env
def supervisor(branch, command):
    """Issue a supervisord command"""
    app_path = _join(env.current, env.github_repo_name)
    pid_path = _join(app_path,"tmp","pids","supervisord.pid")
    if not exists(pid_path):
        _virtualenv(
            app_path,
            "supervisord -c supervisord.%s.conf -j %s" % (branch,pid_path)
        )
    
    _virtualenv(
        _join(env.current, env.github_repo_name),
        "supervisorctl -c supervisord.%s.conf %s" % (branch, command)
    )


def cmd(app=None):
    if app:
        return "%s:*" % app
    else:
        return "all"
    

@_setup_env
def start(branch,app=None):
    """
    Start all or one supervisord process
    
        $ fab start:staging         # starts all
        $ fab start:staging,webapp  # starts the webapp
    
    Where webapp can be any of the names of programs as defined 
    in the supervisord config file's [program:...] sections
    
    """
    return supervisor(branch,"start %s" % cmd(app))

@_setup_env
def stop(branch,app=None):
    """
    Stop all or one supervisord process
    
        $ fab stop:staging         # stops all
        $ fab stop:staging,webapp  # stops the webapp
    
    Where webapp can be any of the names of programs as defined 
    in the supervisord config file's [program:...] sections
    
    """
    return supervisor(branch,"stop %s" % cmd(app))

@_setup_env
def restart(branch,app=None):
    """
    Restart all or one supervisord process
    
        $ fab restart:staging         # restarts all
        $ fab restart:staging,webapp  # restarts the webapp
        
    Where webapp can be any of the names of programs as defined 
    in the supervisord config file's [program:...] sections
    
    """
    return supervisor(branch,"restart %s" % cmd(app))

@_setup_env
def shutdown(branch):
    """
    Shutdown the supervisord daemon
    *** Needed after a redeploy ***
    """
    return supervisor(branch,"shutdown")

@_setup_env
def reload(branch):
    """
    Restart the supervisord daemon
    *** Needed if the supervisord config file is changed ***
    """
    return supervisor(branch,"reload")

#@_setup_env
#def reread(branch):
    #"""
    #Reload the supervisord daemon's configuration files (NAMING ?! :P)
    #"""
    #return supervisor(branch,"reread")

@_setup_env
def cleanup(branch,limit=5):
    """
    Cleanup old releases
    
        $ fab cleanup:staging,limit=10
    
    Remove old releases, the limit argument is optional (defaults to 5).
    """
    run("cd %(releases_path)s && ls -1 . | head --line=-%(limit)s | " \
        "xargs rm -rf " % {
            'releases_path': env.releases_path,
            'limit': limit
        }
    )
