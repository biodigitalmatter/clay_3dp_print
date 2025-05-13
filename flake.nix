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
          pkgs,
          self',
          ...
        }:
        {
          devShells.default =
            (pkgs.buildFHSEnv {
              name = "pixi-env";
              targetPkgs =
                _:
                with pkgs;
                [
                  pixi
                  (pkgs.writeShellApplication {
                    name = "compose";
                    runtimeInputs = [ pkgs.docker-compose ];
                    text = ''
                      docker-compose -f "${inputs.self}/extra/compas_rrc_compose/compose.yaml" "$@"
                    '';
                  })

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
