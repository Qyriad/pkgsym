import os
import os.path
import argparse
from dataclasses import dataclass


@dataclass
class Operation:

    def log(self):
        raise NotImplementedError("Operation.log() must be implemented in subclasses.")

    def perform(self):
        raise NotImplementedError("Operation.perform() must be implemented in subclasses.")

    def log_unperform(self):
        raise NotImplementedError("Operation.log_unperform() must be implemented in subclasses.")

    def unperform(self):
        raise NotImplementedError("Operation.unperform() must be implemented in subclasses.")


@dataclass
class CreateDirectory(Operation):

    # Should be the full, absolute path of the directory to make.
    target: str

    def log(self):
        print(f"created directory '{self.target}'")

    def perform(self):
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

    def log(self):
        print(f"'{self.link}' -> '{self.target}'")

    def perform(self):
        os.symlink(self.target, self.link)
        self.log()

    def log_unperform(self):
        print(f"removed '{self.link}")

    def unperform(self):
        os.remove(self.link)
        self.log_unperform()


HOME_DIR = os.path.expanduser('~')
DEFAULT_PREFIX = os.path.join(HOME_DIR, '.local')


def generate_symlink_operations(install_dir, link_target: os.DirEntry) -> (list[Symlink], list[CreateDirectory]):

    symlink_operations = []
    directory_operations = []

    if link_target.is_file():

        # Easy. Just symlink it.
        full_link_path = os.path.join(install_dir, link_target.name)
        full_target_path = link_target.path
        symlink_operations.append(Symlink(target=full_target_path, link=full_link_path))

    elif link_target.is_dir():

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

    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['link', 'unlink'])
    parser.add_argument('package', action='store', type=str)
    parser.add_argument('--prefix', type=str, default=DEFAULT_PREFIX)

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

        for dirop in directory_operations:
            dirop.perform()

        for symop in symlink_operations:
            symop.perform()

    elif args.action == 'unlink':

        for symop in symlink_operations:
            symop.unperform()

        # Reversed because we have to start at the deepest part of the tree when removing directories.
        for dirop in reversed(directory_operations):
            dirop.unperform()


if __name__ == '__main__':
    main()
