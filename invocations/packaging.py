import getpass
import itertools
import os
import sys
from contextlib import contextmanager
from glob import glob
from shutil import rmtree, copy, copytree
from tempfile import mkdtemp

from invoke.vendor.six import StringIO

from invoke import ctask as task, Collection, run


@contextmanager
def tmpdir():
    tmp = mkdtemp()
    try:
        yield tmp
    finally:
        rmtree(tmp)


def unpack(c, tmp, package, version, git_url=None):
    """
    Download + unpack given package into temp dir ``tmp``.

    Return ``(real_version, source)`` where ``real_version`` is the "actual"
    version downloaded (e.g. if a Git master was indicated, it will be the SHA
    of master HEAD) and ``source`` is the source directory (relative to
    unpacked source) to import into ``<project>/vendor``.
    """
    real_version = version[:]
    source = None
    if git_url:
        pass
    #   git clone into tempdir
    #   git checkout <version>
    #   set target to checkout
    #   if version does not look SHA-ish:
    #       in the checkout, obtain SHA from that branch
    #       set real_version to that value
    else:
        cwd = os.getcwd()
        print("Moving into temp dir %s" % tmp)
        os.chdir(tmp)
        try:
            # Nab from index
            flags = "--download-cache= --download=. --build=build"
            cmd = "pip install %s %s==%s" % (flags, package, version)
            c.run(cmd)
            # Identify basename
            # TODO: glob is bad here because pip install --download gets all
            # dependencies too! ugh.
            zipfile = os.path.basename(glob("*.zip")[0])
            source = os.path.splitext(zipfile)[0]
            # Unzip
            c.run("unzip *.zip")
        finally:
            os.chdir(cwd)
    return real_version, source


@task
def vendorize(c, distribution, version, vendor_dir, package=None,
    git_url=None, license=None):
    """
    Vendorize Python package ``distribution`` at version/SHA ``version``.

    Specify the vendor folder (e.g. ``<mypackage>/vendor``) as ``vendor_dir``.

    For Crate/PyPI releases, ``package`` should be the name of the software
    entry on those sites, and ``version`` should be a specific version number.
    E.g. ``vendorize('lexicon', '0.1.2')``.

    For Git releases, ``package`` should be the name of the package folder
    within the checkout that needs to be vendorized and ``version`` should be a
    Git identifier (branch, tag, SHA etc.) ``git_url`` must also be given,
    something suitable for ``git clone <git_url>``.

    For SVN releases: xxx.

    For packages where the distribution name is not the same as the package
    directory name, give ``package='name'``.

    By default, no explicit license seeking is done -- we assume the license
    info is in file headers or otherwise within the Python package vendorized.
    This is not always true; specify ``license=/path/to/license/file`` to
    trigger copying of a license into the vendored folder from the
    checkout/download (relative to its root.)
    """
    with tmpdir() as tmp:
        package = package or distribution
        target = os.path.join(vendor_dir, package)
        # Unpack source
        real_version, source = unpack(c, tmp, distribution, version, git_url)
        abs_source = os.path.join(tmp, source)
        source_package = os.path.join(abs_source, package)
        # Ensure source package exists
        if not os.path.exists(source_package):
            rel_package = os.path.join(source, package)
            raise ValueError("Source package %s doesn't exist!" % rel_package)
        # Nuke target if exists
        if os.path.exists(target):
            print("Removing pre-existing vendorized folder %s" % target)
            rmtree(target)
        # Perform the copy
        print("Copying %s => %s" % (source_package, target))
        copytree(source_package, target)
        # Explicit license if needed
        if license:
            copy(os.path.join(abs_source, license), target)
        # git commit -a -m "Update $package to $version ($real_version if different)"


@task(name='all')
def all_(c):
    """
    Catchall version-bump/tag/changelog/PyPI upload task.
    """


@task
def changelog(c, target='docs/changelog.rst'):
    """
    Update changelog with new release entry.
    """
    pass


@task
def version(c):
    """
    Update stored project version (e.g. a ``_version.py``.)

    Requires configuration to be effective (since version file is usually kept
    within a project-named directory.
    """
    pass


@task
def tag(c):
    """
    Create a release tag in git.
    """
    from semantic_version import Version
    # TODO: make this configurable or just smarter
    # TODO: make subroutine
    # TODO: is there a way to get this from the same place setup.py does w/o
    # setup.py barfing (since setup() runs at import time and assumes CLI use)?
    name = None
    for path in os.listdir('.'):
        if (
            path != 'tests'
            and os.path.isdir(path)
            and os.path.exists(os.path.join(path, '__init__.py'))
        ):
            name = path
            break
    if name is None:
        sys.exit("Unable to find a local Python package!")
    package = __import__("{0}".format(name), fromlist=['_version']) 
    # TODO: document assumption about our usual _version setup
    current_version = Version(package._version.__version__) # buffalo buffalo
    msg = "Found package {0.__name__!r} at version {1}"
    print(msg.format(package, current_version))
    # TODO: document assumption about semantic versioning in tags
    tags = []
    for tagstr in run("git tag", hide=True).stdout.strip().split('\n'):
        try:
            tags.append(Version(tagstr))
        except ValueError: # just skip non-semver version strings
            pass
    tags = sorted(tags)
    # TODO: doc assumption that _version has been updated prior to this step...
    # TODO: also, maybe run "did you update that yet" test here as well as in
    # its own task, or set as pre-task
    if tags[-1] != current_version:
        msg = "Current version {0} != latest tag {1}, creating new tag"
        print(msg.format(current_version, tags[-1]))
        run("git tag {0}".format(current_version))
    else:
        msg = "Already see a tag for {0}, doing nothing"
        print(msg.format(current_version))


@task
def push(c):
    """
    Push tag/changelog/version changes to Git origin.
    """
    # TODO: or should this be distributed amongst the appropriate tasks?
    pass


@task(aliases=['upload'])
def publish(c, sdist=True, wheel=False, index=None, sign=False, dry_run=False):
    """
    Publish code to PyPI or index of choice.

    All parameters save ``dry_run`` honor config settings of the same name,
    under the ``packaging`` tree. E.g. say ``.configure({'packaging': {'wheel':
    True}})`` to force building wheel archives by default.

    :param bool sdist:
        Whether to upload sdists/tgzs.

    :param bool wheel:
        Whether to upload wheels (requires the ``wheel`` package from PyPI).

    :param str index:
        Custom upload index URL.

        By default, uses whatever the invoked ``pip`` is configured to use.

    :param bool sign:
        Whether to sign the built archive(s) via GPG.

    :param bool dry_run:
        Skip actual publication step if ``True``.
    """
    # Config hooks
    config = c.config.get('packaging', {})
    sdist = config.get('sdist', sdist)
    wheel = config.get('wheel', wheel)
    index = config.get('index', index)
    sign = config.get('sign', sign)
    # Sanity
    if not sdist and not wheel:
        sys.exit("You said no sdists and no wheels...what DO you want to publish exactly?") # noqa
    # Build, into controlled temp dir (avoids attempting to re-upload old
    # files)
    with tmpdir() as tmp:
        # Build
        parts = ["python", "setup.py"]
        dist_dir = "-d {0}".format(tmp)
        if sdist:
            parts.append("sdist")
            parts.append(dist_dir)
        if wheel:
            parts.append("bdist_wheel")
            parts.append(dist_dir)
        c.run(" ".join(parts))
        # Obtain list of archive filenames, then ensure any wheels come first
        # so their improved metadata is what PyPI sees initially (otherwise, it
        # only honors the sdist's lesser data).
        archives = list(itertools.chain.from_iterable(
            glob(os.path.join(tmp, '*.{0}'.format(extension)))
            for extension in ('whl', 'tar.gz')
        ))
        # Sign each archive in turn
        if sign:
            prompt = "Please enter GPG passphrase for signing: "
            input_ = StringIO(getpass.getpass(prompt) + "\n")
            for archive in archives:
                cmd = "gpg --detach-sign -a --passphrase-fd 0 {0}"
                c.run(cmd.format(archive), in_stream=input_)
                input_.seek(0) # So it can be replayed by subsequent iterations
        # Upload
        parts = ["twine", "upload"]
        if index:
            index_arg = "-r {0}".format(index)
        if index:
            parts.append(index_arg)
        paths = archives + [os.path.join(tmp, "*.asc")]
        parts.extend(paths)
        cmd = " ".join(parts)
        if dry_run:
            print("Would publish via: {0}".format(cmd))
            print("Files that would be published:")
            c.run("ls -l {0}".format(" ".join(paths)))
        else:
            c.run(cmd)


release = Collection('release', changelog, version, tag, push, publish)
release.add_task(all_, default=True)
