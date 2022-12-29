# pkgsym — A poor man's package manager (like `brew link` but without the brew)

## Usage and Motivation

*pkgsym* is a utility to symlink and un-symlink a package under from a self-contained directory to a prefix.

Say you're installing a package from source without your package manager. You perform the Unix magic invocation (or some on Windows):
```sh
./configure --prefix=/usr/local
make
sudo make install
```

Now you have a bunch of stuff under `/usr/local`. How do you determine what files came from what package? How do you uninstall the package? (Not all build systems provide a `make uninstall`.)

Enter `pkgsym`. Now you can install the package to a self-contained directory, something like this:
```sh
./configure --prefix=/usr/local/opt/foopkg
make
sudo make install
```
So now `foo`'s command is something like `/usr/local/opt/foo/bin/foocmd`, which definitely isn't going to be in your PATH by default, and you probably don't want to add every odd directory of `/usr/local/opt/*/bin` to your PATH either.

[Homebrew](https://brew.sh) takes the approach of symlinking packages into a prefix. That's exactly what pkgsym does. Now you can finish off your package installation:
```sh
sudo pkgsym link --system foo
```

That will take any directories under `/usr/local/opt/foo/` and symlink their *contents* to `/usr/local/{dir}/{file}`, creating any directories as necessary. So `/usr/local/opt/foo/bin/cmd` is symlinked to `/usr/local/bin/foocmd`, `/usr/local/opt/foo/lib/libfoo.so` is symlinked to `/usr/local/lib/libfoo.so`, etc. Subdirectories are handled recursively.

Now to uninstall the package, simply run:
```sh
sudo pkgsym unlink --system foo
sudo rm -rf /usr/local/opt/foo
```


### Hey, what's that --system?

pkgsym supports any arbitrary package prefix. You could install foo to `C:\Packages\opt\foo` if you want, and then have `foocmd` as `C:\Packages\bin\foocmd` with something like:
```sh
cmake -B build -DCMAKE_INSTALL_PREFIX=C:/Packages/opt/foo
cmake --build build
cmake --install build
pkgsym --prefix C:/Packages link foo
```
(Forward slashes and backslashes are both supported for Windows).

`--system` is a shortcut for `--prefix /usr/local`, and `--user` is a shortcut for `--prefix ~/.local`. `--user` is the default, but is still available as an explicit argument for clarity.

## What made this necessary? Are you okay?

Listen installing packages from source on Windows sucks okay? This script is basically a glorified `for i in $prefix/opt/**/*; do ln -s "${i:bash/string/manipulation}"`, but with it as my hammer I've been able to manage dependency hell on Windows with ad-hoc packages.

If you have a real package manager available to you for the thing you want, *definitely* use that instead. pkgsym is for the unfortunate cases where you do not.
