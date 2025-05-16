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
          devShells.default =
            (pkgs.buildFHSEnv {
              name = "pixi-env";

              runScript =
                let
                  fish_cfg_d = pkgs.writeTextDir "clay_3dp_print-fish_cfg.d" ''
                    abbr --add compose docker-compose -f "${inputs.self}/extra/compas_rrc_compose/compose.yaml"
                    abbr --add run pixi run clay_3dp_print
                  '';
                in
                lib.getExe (
                  pkgs.wrapFish {
                    pluginPkgs = with pkgs.fishPlugins; [ ];
                    completionDirs = [ ];
                    functionDirs = [ ];
                    confDirs = [ fish_cfg_d ];
                  }
                );

              targetPkgs =
                _:
                with pkgs;
                [
                  docker-compose
                  pixi
                ]
                ++ (builtins.attrValues config.treefmt.build.programs);
            }).env;

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
