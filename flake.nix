{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        inherit (builtins) attrValues;

        pkgsym = pkgs.python3Packages.buildPythonApplication {
          pname = "pkgsym";
          version = "0.2.4";
          format = "pyproject";
          src = ./.;

          meta = {
            description = "Poor man's package manager, symlink edition";
            homepage = "https://github.com/Qyriad/pkgsym";
            license = pkgs.lib.licenses.mit;

            # In theory, this works anywhere Python does.
            platforms = pkgs.python3.meta.platforms;
          };

          nativeBuildInputs = attrValues {
            inherit (pkgs.python3Packages)
              setuptools
              wheel
            ;
          };

        }; # buildPythonApplication
      in {
        packages.default = pkgsym;

        devShells.default = pkgs.mkShell {
          packages = attrValues {
            inherit (pkgs.python3Packages)
              build
              twine
            ;
          } ++ [
            pkgs.pyright
          ];

          inputsFrom = [ pkgsym ];
        };
      }

    ) # eachDefaultSystem
  ; # outputs
}
