{ pkgs }:
# Fallback Nix manifest for Repls that honor replit.nix instead of the
# inline [nix] block in .replit. Keeps bleak available so the grader
# and Inkbird BLE driver boot cleanly.
{
  deps = [
    pkgs.nodejs_24
    pkgs.postgresql_16
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.bleak
    pkgs.bluez
  ];
}
