{
  lib,
  python3,
}:

let
  inherit (python3.pkgs)
    buildPythonApplication
    setuptools
    wheel
  ;
in
  buildPythonApplication {
    pname = "pkgsym";
    version = "0.2.4";
    format = "pyproject";

    src = lib.cleanSource ./.;

    nativeBuildInputs = [
      setuptools
      wheel
    ];

    meta = {
      description = "Poor man's package manager, symlink edition";
      homepage = "https://github.com/Qyriad/pkgsym";
      license = lib.licenses.mit;

      # In theory, this works anywhere Python does.
      platforms = python3.meta.platforms;
    };
  }
