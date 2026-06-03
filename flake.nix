{
  description = "Pixi env for clay_3dp_print";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default-linux";
    treefmt-nix.url = "github:numtide/treefmt-nix";
  };
  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.treefmt-nix.flakeModule
      ];
      systems = import inputs.systems;
      perSystem =
        {
          config,
          lib,
          pkgs,
          self',
          ...
        }:
        {
          devShells.default = pkgs.mkShell {
            name = "clay_3dp_print-dev_shell";
            inputsFrom = [ config.treefmt.build.devShell ];
            buildInputs = with pkgs; [
              basedpyright
              config.treefmt.build.wrapper
              docker-compose
              pixi
            ];
          };

          treefmt = {
            programs = {
              ruff-check.enable = true;
              ruff-format.enable = true;
              nixfmt.enable = true;
              taplo.enable = true; # toml
            };
          };
        };
    };
}
