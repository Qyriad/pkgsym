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

        pkgsym = pkgs.callPackage ./package.nix { };

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
