import os
import sys
import os.path
import errno
import argparse
import itertools
import traceback
from dataclasses import dataclass
from typing import Tuple, List


HOME_DIR = os.path.expanduser('~')
DEFAULT_PREFIX = os.path.join(HOME_DIR, '.local')
DEFAULT_OPT = "opt"


@dataclass
class Operation:

    def error(self, error_cls: type, err_code: int):
        """ Creates a Python exception of type `error_cls` with errno `err_code` for a failure of this operation. """
        raise NotImplementedError("Operation.error() must be implemented in subclass.")

    def check(self, unperform=False):
        """ Tries to check if this operation can be performed without error (not foolproof). Should raise self.error() if fails."""
        # We're trying to ask for permission rather than begging for forgiveness, but if we *can*, we'd rather
        # let the user know that their operation will fail *before* any changes are made to the disk.
        raise NotImplementedError("Operation.check() must be implemented in subclass.")

    def check_unperform(self):
        """ Tries to check if this operation can be unperformed without error (not foolproof). """
        # We're trying to ask for permission rather than begging for forgiveness, but if we *can*, we'd rather
        # let the user know that their operation will fail *before* any changes are made to the disk.
        raise NotImplementedError("Operation.check_unperform() must be implemented in subclass.")

    def log(self, unperform=False):
        raise NotImplementedError("Operation.log() must be implemented in subclasses.")

    def perform(self, unperform=False):
        raise NotImplementedError("Operation.perform() must be implemented in subclasses.")

    def log_unperform(self):
        raise NotImplementedError("Operation.log_unperform() must be implemented in subclasses.")

    def unperform(self):
        raise NotImplementedError("Operation.unperform() must be implemented in subclasses.")


@dataclass
class CreateDirectory(Operation):

    # Should be the full, absolute path of the directory to make.
    target: str

    def error(self, error_cls: type, err_code: int):
        e = error_cls(err_code, os.strerror(err_code))
        e.filename = self.target
        return e

    def check(self, unperform=False):
        if unperform:
            return self.check_unperform()

        if os.path.exists(self.target):
            raise self.error(FileExistsError, errno.EEXIST)

    def check_unperform(self):
        # No-op. This will probably only fail for things like permission errors, which are harder to detect and
        # less likely to end up in a mixed state on disk.
        # We'll beg for forgiveness in that case.
        pass

    def log(self, unperform=False):
        if unperform:
            return self.log_unperform()

        print(f"created directory '{self.target}'")

    def perform(self, unperform=False):
        if unperform:
            return self.unperform()

        os.mkdir(self.target)
        self.log()

    def log_unperform(self):
        print(f"removed directory '{self.target}'")

    def unperform(self):

        if not os.listdir(self.target):
            os.rmdir(self.target)
            self.log_unperform()


@dataclass
class Symlink(Operation):

    # Should be the full, absolute path to the target.
    target: str
    # Should be the full, absolute path to the link.
    link: str

    def error(self, error_cls: type, err_code: int):
        e = error_cls(err_code, os.strerror(err_code))
        e.filename = self.link
        e.filename2 = self.target
        return e

    def check(self, unperform=False):
        if unperform:
            return self.check_unperform()

        if os.path.exists(self.link):
            raise self.error(FileExistsError, errno.EEXIST)
        if not os.path.exists(self.target):
            raise self.error(FileNotFoundError, errno.ENOENT)

    def check_unperform(self):
        if not os.path.exists(self.link):
            raise self.error(FileNotFoundError, errno.ENOENT)

    def log(self, unperform=False):
        if unperform:
            return self.log_unperform()

        print(f"'{self.link}' -> '{self.target}'")

    def perform(self, unperform=False):
        if unperform:
            return self.unperform()

        os.symlink(self.target, self.link)
        self.log()

    def log_unperform(self):
        print(f"removed '{self.link}")

    def unperform(self):
        os.remove(self.link)
        self.log_unperform()



def generate_symlink_operations(install_dir, link_target: os.DirEntry) -> Tuple[List[Symlink], List[CreateDirectory]]:
    """ Recursively generate the symlink and mkdir operations necessary to create link_target's directory tree. """

    symlink_operations = []
    directory_operations = []

    if link_target.is_file():

        # Easy. Just symlink it.
        full_link_path = os.path.join(install_dir, link_target.name)
        full_target_path = link_target.path
        symlink_operations.append(Symlink(target=full_target_path, link=full_link_path))

    elif link_target.is_dir():

        # If it's a directory (which is the case for the first call of this function, e.g.
        # generate_symlink_operations("/home/user/.local", "/home/user/.local/opt/neovim"))
        # then we need to create all descendent directories and symlink all children files of
        # those direrctories.

        full_subdir_path = os.path.join(install_dir, link_target.name)
        if not os.path.exists(full_subdir_path):
            directory_operations.append(CreateDirectory(full_subdir_path))

        elif not os.path.isdir(full_subdir_path):
            # If the path we need exists, but is a file instead of a directory, we have a problem.
            raise ValueError(f"Path '{full_subdir_path}' already exists as non-directory!")

        for entry in os.scandir(link_target.path):

            symops, dirops = generate_symlink_operations(full_subdir_path, entry)
            symlink_operations.extend(symops)
            directory_operations.extend(dirops)


    return (symlink_operations, directory_operations)


def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('action', choices=['link', 'unlink'],
        help="Link or unlink a package under the self-contained directory to the prefix",
    )
    parser.add_argument('package', action='store', type=str,
        help="The package name to link or unlink -- should be the directory under $prefix/opt that contains the package",
    )
    parser.add_argument('--prefix', type=str, default=DEFAULT_PREFIX,
        help="Directory to use as a prefix for package managemnt",
    )
    parser.add_argument('--system', action='store_const', const='/usr/local', dest='prefix',
        default=argparse.SUPPRESS,
        help='Shortcut for --prefix /usr/local',
    )
    parser.add_argument('--user', action='store_const', const=DEFAULT_PREFIX, dest='prefix',
        default=argparse.SUPPRESS,
        help='Shortcut for --prefix ~/.local (default)',
    )
    parser.add_argument('--opt', type=str, default=DEFAULT_OPT, metavar='OPT_DIR',
        help="Directory under prefix that contains self-contained installs",
    )
    parser.add_argument('-n', '--dry-run', action='store_true',
        help="Print operations without executing",
    )
    parser.add_argument('--ignore-errors', action='store_true',
        help="Ignore IO errors (e.g. link name already exists) when linking or unlinking. Can be useful to get out of a mixed state.",
    )

    args = parser.parse_args()

    pkgdir = os.path.join(args.prefix, 'opt', args.package)

    if not os.path.isdir(pkgdir):
        parser.error(f"{pkgdir} must be an installed package directory")


    # Each path in subdirs will be a directory of the form `$prefix/opt/$pkg/subdir`.
    # We will need to recursively create any directories that don't already exist, and symlink any files.
    # For the $prefix/opt/$pkg case and *only* that case, we don't want to include files, only directories.

    subdirs = [ent for ent in os.scandir(pkgdir) if ent.is_dir()]

    symlink_operations = []
    directory_operations = []

    for subdir in subdirs:
        symops, dirops = generate_symlink_operations(args.prefix, subdir)
        symlink_operations.extend(symops)
        directory_operations.extend(dirops)

    if args.action == 'link':
        operations = list(itertools.chain(directory_operations, symlink_operations))
        unperform = False
    elif args.action == 'unlink':
        # The order is reversed from above because we have to start at the deepest part
        # of the tree when removing directories.
        operations = list(itertools.chain(symlink_operations, directory_operations))
        unperform = True
    else:
        raise ValueError("Unreachable")

    if not args.ignore_errors:

        for operation in operations:
            try:
                operation.check(unperform)
            except OSError as e:
                traceback.print_exception(e)
                print("Note: the above error occurred as a check. No disk operations have been performed.")
                return e.errno

        for operation in operations:
            if args.dry_run:
                operation.log(unperform)
            else:
                try:
                    operation.perform(unperform)
                except OSError as e:
                    if args.ignore_errors:
                        print(f"Ignoring error {e}")
                    else:
                        raise e


if __name__ == '__main__':
    sys.exit(main())
